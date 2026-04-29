"""Application configuration via environment variables."""

import os
from pathlib import Path


def _load_dotenv():
    """Load .env file if it exists."""
    env_path = Path(os.getenv("ENV_FILE", ".env"))
    if not env_path.is_absolute():
        for candidate in [Path.cwd() / env_path, Path(__file__).parent.parent.parent / env_path]:
            if (candidate).exists():
                env_path = candidate
                break
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv()


APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-session-secret")

GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "change-me")

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", str(DATA_DIR / "cache")))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "gateway.sqlite"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "1000"))
MAX_CONCURRENT_SYNTHESIS = int(os.getenv("MAX_CONCURRENT_SYNTHESIS", "2"))
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "60"))
DEFAULT_RETRY_COUNT = int(os.getenv("DEFAULT_RETRY_COUNT", "1"))

VERSION = os.getenv("VERSION", "0.1.0")
