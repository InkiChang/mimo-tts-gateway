"""SQLite database initialization and helpers."""

import sqlite3
import threading
from pathlib import Path

from . import config

_local = threading.local()


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def close_db():
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            provider_type TEXT NOT NULL DEFAULT 'mimo_chat_completions',
            base_url TEXT NOT NULL,
            endpoint TEXT NOT NULL DEFAULT '/v1/chat/completions',
            api_key TEXT,
            auth_type TEXT NOT NULL DEFAULT 'bearer',
            auth_header_name TEXT DEFAULT 'Authorization',
            model TEXT NOT NULL,
            default_voice TEXT,
            request_mode TEXT NOT NULL DEFAULT 'chat_completions_audio',
            response_mode TEXT NOT NULL DEFAULT 'base64_audio_in_choices',
            output_format TEXT NOT NULL DEFAULT 'mp3',
            timeout_seconds INTEGER NOT NULL DEFAULT 60,
            retry_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            provider_id INTEGER NOT NULL,
            voice TEXT,
            style TEXT,
            format TEXT NOT NULL DEFAULT 'mp3',
            speed REAL NOT NULL DEFAULT 1.0,
            text_prefix TEXT,
            text_suffix TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(provider_id) REFERENCES providers(id)
        );

        CREATE TABLE IF NOT EXISTS tts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            provider_id INTEGER,
            model TEXT,
            voice TEXT,
            text_hash TEXT,
            style_hash TEXT,
            format TEXT,
            file_path TEXT NOT NULL,
            size_bytes INTEGER DEFAULT 0,
            hit_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_hit_at TEXT
        );

        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            path TEXT NOT NULL,
            provider_id INTEGER,
            preset_name TEXT,
            raw_text_length INTEGER,
            normalized_text_length INTEGER,
            text_hash TEXT,
            cache_hit INTEGER DEFAULT 0,
            status_code INTEGER,
            latency_ms INTEGER,
            error_type TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    db.commit()


def get_setting(key: str, default: str | None = None) -> str | None:
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )
    db.commit()


def dict_from_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)
