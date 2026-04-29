"""Audio file cache service."""

import asyncio
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .. import database
from ..database import dict_from_row, get_db


in_flight: dict[str, asyncio.Lock] = {}


def _cache_dir_for_key(cache_key: str, cache_root: Path) -> Path:
    subdir = cache_root / cache_key[:2] / cache_key[2:4]
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def compute_cache_key(
    provider_id: int,
    provider_base_url: str,
    request_mode: str,
    response_mode: str,
    model: str,
    voice: str,
    style: str,
    text: str,
    fmt: str,
    speed: float,
    text_prefix: str | None = None,
    text_suffix: str | None = None,
) -> str:
    """Generate deterministic cache key from all relevant parameters."""
    payload = json.dumps(
        {
            "provider_id": provider_id,
            "provider_base_url": str(provider_base_url).rstrip("/"),
            "request_mode": request_mode,
            "response_mode": response_mode,
            "model": model,
            "voice": voice,
            "style": style or "",
            "text": text,
            "format": fmt,
            "speed": speed,
            "text_prefix": text_prefix or "",
            "text_suffix": text_suffix or "",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_cache(cache_key: str, cache_root: Path) -> dict | None:
    """Check if cache entry exists in DB and file exists on disk."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM tts_cache WHERE cache_key = ?", (cache_key,)
    ).fetchone()

    if not row:
        return None

    cache_entry = dict_from_row(row)
    file_path = Path(cache_entry["file_path"])
    if not file_path.exists():
        db.execute("DELETE FROM tts_cache WHERE cache_key = ?", (cache_key,))
        db.commit()
        return None

    db.execute(
        "UPDATE tts_cache SET hit_count = hit_count + 1, last_hit_at = datetime('now') WHERE cache_key = ?",
        (cache_key,),
    )
    db.commit()
    cache_entry["hit_count"] += 1
    return cache_entry


def save_cache(
    cache_key: str,
    provider_id: int,
    model: str,
    voice: str,
    text_hash: str,
    style: str | None,
    fmt: str,
    audio_data: bytes,
    cache_root: Path,
) -> dict:
    """Save audio to cache atomically."""
    cache_dir = _cache_dir_for_key(cache_key, cache_root)
    file_path = cache_dir / f"{cache_key}.{fmt}"

    # Atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=f".{fmt}", dir=cache_dir)
    try:
        with open(tmp_fd, "wb") as f:
            f.write(audio_data)
        Path(tmp_path).rename(file_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    style_hash_val = hashlib.sha256((style or "").encode("utf-8")).hexdigest()[:16]
    size = len(audio_data)

    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO tts_cache
           (cache_key, provider_id, model, voice, text_hash, style_hash, format,
            file_path, size_bytes, hit_count, created_at, last_hit_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))""",
        (
            cache_key,
            provider_id,
            model,
            voice,
            text_hash,
            style_hash_val,
            fmt,
            str(file_path),
            size,
        ),
    )
    db.commit()

    return {
        "cache_key": cache_key,
        "file_path": str(file_path),
        "size_bytes": size,
        "hit_count": 1,
    }


def get_cache_stats(cache_root: Path) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size FROM tts_cache"
    ).fetchone()
    return {
        "file_count": row["count"],
        "total_size_bytes": row["total_size"],
    }


def clear_all_cache(cache_root: Path):
    db = get_db()
    db.execute("DELETE FROM tts_cache")
    db.commit()
    if cache_root.exists():
        shutil.rmtree(cache_root)
        cache_root.mkdir(parents=True, exist_ok=True)
