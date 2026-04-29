"""Preset management service."""

from .. import database
from ..database import dict_from_row, get_db, get_setting, set_setting


def get_preset(preset_id: int) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM presets WHERE id = ?", (preset_id,)).fetchone()
    return dict_from_row(row)


def get_preset_by_name(name: str) -> dict | None:
    db = get_db()
    row = db.execute(
        "SELECT * FROM presets WHERE name = ? AND enabled = 1", (name,)
    ).fetchone()
    return dict_from_row(row)


def get_enabled_presets() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM presets WHERE enabled = 1").fetchall()
    return [dict(r) for r in rows]


def get_all_presets() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM presets ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def create_preset(data: dict) -> dict:
    db = get_db()
    cursor = db.execute(
        """INSERT INTO presets
           (name, provider_id, voice, style, format, speed,
            text_prefix, text_suffix, enabled)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["name"],
            data["provider_id"],
            data.get("voice"),
            data.get("style"),
            data.get("format", "mp3"),
            data.get("speed", 1.0),
            data.get("text_prefix"),
            data.get("text_suffix"),
            data.get("enabled", 1),
        ),
    )
    db.commit()
    return get_preset(cursor.lastrowid)


def update_preset(preset_id: int, data: dict) -> dict | None:
    existing = get_preset(preset_id)
    if not existing:
        return None

    fields = [
        "name", "provider_id", "voice", "style", "format", "speed",
        "text_prefix", "text_suffix", "enabled",
    ]
    merged = {f: data.get(f, existing.get(f)) for f in fields}

    db = get_db()
    db.execute(
        """UPDATE presets SET
           name=?, provider_id=?, voice=?, style=?, format=?,
           speed=?, text_prefix=?, text_suffix=?, enabled=?,
           updated_at=datetime('now')
           WHERE id=?""",
        (
            merged["name"], merged["provider_id"], merged["voice"],
            merged["style"], merged["format"], merged["speed"],
            merged["text_prefix"], merged["text_suffix"],
            merged["enabled"], preset_id,
        ),
    )
    db.commit()
    return get_preset(preset_id)


def delete_preset(preset_id: int) -> bool:
    db = get_db()
    cursor = db.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
    db.commit()
    return cursor.rowcount > 0


def get_default_preset_name() -> str:
    return get_setting("default_preset_name", "default")


def set_default_preset_name(name: str):
    set_setting("default_preset_name", name)
