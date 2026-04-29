"""Provider management service."""

from .. import database
from ..database import dict_from_row, get_db, get_setting, set_setting


def get_provider(provider_id: int) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return dict_from_row(row)


def get_enabled_providers() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM providers WHERE enabled = 1").fetchall()
    return [dict(r) for r in rows]


def get_all_providers() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM providers ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def create_provider(data: dict) -> dict:
    db = get_db()
    cursor = db.execute(
        """INSERT INTO providers
           (name, enabled, provider_type, base_url, endpoint, api_key,
            auth_type, auth_header_name, model, default_voice,
            request_mode, response_mode, output_format,
            timeout_seconds, retry_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["name"],
            data.get("enabled", 1),
            data.get("provider_type", "mimo_chat_completions"),
            data["base_url"],
            data.get("endpoint", "/v1/chat/completions"),
            data.get("api_key"),
            data.get("auth_type", "bearer"),
            data.get("auth_header_name", "Authorization"),
            data["model"],
            data.get("default_voice"),
            data.get("request_mode", "chat_completions_audio"),
            data.get("response_mode", "base64_audio_in_choices"),
            data.get("output_format", "mp3"),
            data.get("timeout_seconds", 60),
            data.get("retry_count", 1),
        ),
    )
    db.commit()
    return get_provider(cursor.lastrowid)


def update_provider(provider_id: int, data: dict) -> dict | None:
    existing = get_provider(provider_id)
    if not existing:
        return None

    fields = [
        "name", "enabled", "provider_type", "base_url", "endpoint", "api_key",
        "auth_type", "auth_header_name", "model", "default_voice",
        "request_mode", "response_mode", "output_format",
        "timeout_seconds", "retry_count",
    ]
    merged = {f: data.get(f, existing.get(f)) for f in fields}

    db = get_db()
    db.execute(
        """UPDATE providers SET
           name=?, enabled=?, provider_type=?, base_url=?, endpoint=?,
           api_key=?, auth_type=?, auth_header_name=?, model=?,
           default_voice=?, request_mode=?, response_mode=?,
           output_format=?, timeout_seconds=?, retry_count=?,
           updated_at=datetime('now')
           WHERE id=?""",
        (
            merged["name"], merged["enabled"], merged["provider_type"],
            merged["base_url"], merged["endpoint"], merged["api_key"],
            merged["auth_type"], merged["auth_header_name"], merged["model"],
            merged["default_voice"], merged["request_mode"],
            merged["response_mode"], merged["output_format"],
            merged["timeout_seconds"], merged["retry_count"], provider_id,
        ),
    )
    db.commit()
    return get_provider(provider_id)


def delete_provider(provider_id: int) -> bool:
    db = get_db()
    cursor = db.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
    db.commit()
    return cursor.rowcount > 0


def get_default_provider_id() -> int | None:
    val = get_setting("default_provider_id")
    return int(val) if val else None


def set_default_provider_id(provider_id: int):
    set_setting("default_provider_id", str(provider_id))
