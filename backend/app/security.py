"""Security helpers: gateway token auth and admin session."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import config, database


def create_signer():
    return URLSafeTimedSerializer(config.SESSION_SECRET)


def verify_gateway_token(token: str) -> bool:
    if not token:
        return False
    return secrets.compare_digest(token, config.GATEWAY_TOKEN)


def get_token_from_request(request: Request) -> str | None:
    token = request.query_params.get("token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    return token


def require_gateway_token(request: Request):
    token = get_token_from_request(request)
    if not token or not verify_gateway_token(token):
        raise HTTPException(status_code=401, detail="Invalid or missing gateway token")
    return token


def create_admin_session(username: str) -> str:
    signer = create_signer()
    return signer.dumps({"username": username, "iat": datetime.now(UTC).isoformat()})


def verify_admin_session(token: str) -> dict | None:
    signer = create_signer()
    try:
        data = signer.loads(token, max_age=86400)
        return data
    except BadSignature:
        return None


def check_admin_password(username: str, password: str) -> bool:
    return (
        secrets.compare_digest(username, config.ADMIN_USERNAME)
        and secrets.compare_digest(password, config.ADMIN_PASSWORD)
    )


def require_admin(request: Request):
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_data = verify_admin_session(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session_data
