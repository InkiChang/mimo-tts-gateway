"""Request logging service."""

import time

from .. import database
from ..database import get_db


def log_request(
    path: str,
    provider_id: int | None = None,
    preset_name: str | None = None,
    raw_text_length: int = 0,
    normalized_text_length: int = 0,
    text_hash: str | None = None,
    cache_hit: bool = False,
    status_code: int = 200,
    latency_ms: int = 0,
    error_type: str | None = None,
    error_message: str | None = None,
):
    db = get_db()
    db.execute(
        """INSERT INTO request_logs
           (path, provider_id, preset_name, raw_text_length,
            normalized_text_length, text_hash, cache_hit,
            status_code, latency_ms, error_type, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            path,
            provider_id,
            preset_name,
            raw_text_length,
            normalized_text_length,
            text_hash,
            1 if cache_hit else 0,
            status_code,
            latency_ms,
            error_type,
            error_message[:200] if error_message else None,
        ),
    )
    db.commit()


def get_recent_logs(limit: int = 50) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM request_logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
