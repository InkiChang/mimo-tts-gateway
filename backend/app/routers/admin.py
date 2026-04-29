"""Admin endpoints: login, provider/preset management, test, logs."""

import json
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import config
from ..database import init_db
from ..security import (
    check_admin_password,
    create_admin_session,
    require_admin,
    verify_admin_session,
)
from ..services import (
    cache_service,
    log_service,
    preset_service,
    provider_service,
    tts_service,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_template_dir = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    autoescape=select_autoescape(["html"]),
)


def _render(name: str, context: dict | None = None) -> HTMLResponse:
    template = _jinja_env.get_template(name)
    return HTMLResponse(template.render(**(context or {})))


def _check_auth(request: Request) -> bool:
    session = request.cookies.get("session")
    if not session:
        return False
    return verify_admin_session(session) is not None


# ---- Login ----

@router.get("/login")
async def login_page(request: Request):
    if _check_auth(request):
        return RedirectResponse(url="/admin/setup", status_code=303)
    return _render("login.html", {})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_admin_password(username, password):
        session_token = create_admin_session(username)
        response = RedirectResponse(url="/admin/setup", status_code=303)
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
        return response

    return _render("login.html", {"error": "Invalid username or password"},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("session")
    return response


# ---- Setup Page ----

@router.get("/setup")
async def setup_page(request: Request):
    session = require_admin(request)
    providers = provider_service.get_all_providers()
    presets = preset_service.get_all_presets()
    return _render(
        "setup.html",
        {

            "providers": providers,
            "presets": presets,
        },
    )


# ---- Provider CRUD API ----

@router.post("/api/providers")
async def create_provider(request: Request):
    session = require_admin(request)
    form = await request.form()
    data = {
        "name": form["name"],
        "provider_type": form.get("provider_type", "mimo_chat_completions"),
        "base_url": form["base_url"],
        "api_key": form.get("api_key", ""),
        "model": form["model"],
        "default_voice": form.get("default_voice", ""),
        "output_format": form.get("output_format", "mp3"),
        "endpoint": form.get("endpoint", "/v1/chat/completions"),
        "auth_type": form.get("auth_type", "bearer"),
        "auth_header_name": form.get("auth_header_name", "Authorization"),
        "timeout_seconds": int(form.get("timeout_seconds", "60")),
        "retry_count": int(form.get("retry_count", "1")),
    }
    provider = provider_service.create_provider(data)

    # If it's the first provider, set as default
    if provider_service.get_default_provider_id() is None:
        provider_service.set_default_provider_id(provider["id"])

    return RedirectResponse(url="/admin/setup", status_code=303)


@router.get("/api/providers/{provider_id}/edit")
async def edit_provider_form(request: Request, provider_id: int):
    session = require_admin(request)
    provider = provider_service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _render(
        "provider_form.html",
        {"provider": provider, "editing": True},
    )


@router.post("/api/providers/{provider_id}/edit")
async def update_provider(request: Request, provider_id: int):
    session = require_admin(request)
    form = await request.form()
    data = {k: v for k, v in form.items() if v}
    if "timeout_seconds" in data:
        data["timeout_seconds"] = int(data["timeout_seconds"])
    if "retry_count" in data:
        data["retry_count"] = int(data["retry_count"])
    provider_service.update_provider(provider_id, data)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/providers/{provider_id}/delete")
async def delete_provider(request: Request, provider_id: int):
    session = require_admin(request)
    provider_service.delete_provider(provider_id)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/providers/{provider_id}/set-default")
async def set_default_provider(request: Request, provider_id: int):
    session = require_admin(request)
    provider_service.set_default_provider_id(provider_id)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/providers/{provider_id}/toggle")
async def toggle_provider(request: Request, provider_id: int):
    session = require_admin(request)
    provider = provider_service.get_provider(provider_id)
    if provider:
        provider_service.update_provider(
            provider_id, {"enabled": 0 if provider["enabled"] else 1}
        )
    return RedirectResponse(url="/admin/setup", status_code=303)


# ---- Provider Test ----

@router.post("/api/providers/{provider_id}/test")
async def test_provider(request: Request, provider_id: int):
    session = require_admin(request)
    form = await request.form()
    text = form.get("text", "你好，这是 mimo-tts-gateway 测试。")
    voice = form.get("voice", "")
    style = form.get("style", "")
    fmt = form.get("format", "mp3")

    provider = provider_service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        result = await tts_service.test_synthesis(provider, voice, style, fmt, text)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)[:200]}, status_code=422
        )


# ---- Test Audio ----

@router.get("/api/test-audio/{filename}")
async def get_test_audio(filename: str):
    cache_key = filename.rsplit(".", 1)[0]
    cached = cache_service.check_cache(cache_key, config.CACHE_DIR)
    if not cached:
        raise HTTPException(status_code=404, detail="Audio not found")

    with open(cached["file_path"], "rb") as f:
        audio = f.read()

    media_type = "audio/mpeg"
    if filename.endswith(".wav"):
        media_type = "audio/wav"
    elif filename.endswith(".opus"):
        media_type = "audio/opus"
    elif filename.endswith(".ogg"):
        media_type = "audio/ogg"

    return Response(content=audio, media_type=media_type)


# ---- Preset CRUD API ----

@router.post("/api/presets")
async def create_preset(request: Request):
    session = require_admin(request)
    form = await request.form()
    data = {
        "name": form["name"],
        "provider_id": int(form["provider_id"]),
        "voice": form.get("voice", ""),
        "style": form.get("style", ""),
        "format": form.get("format", "mp3"),
        "speed": float(form.get("speed", "1.0")),
        "text_prefix": form.get("text_prefix", ""),
        "text_suffix": form.get("text_suffix", ""),
    }
    preset_service.create_preset(data)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.get("/api/presets/{preset_id}/edit")
async def edit_preset_form(request: Request, preset_id: int):
    session = require_admin(request)
    preset = preset_service.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    providers = provider_service.get_enabled_providers()
    return _render(
        "preset_form.html",
        {"preset": preset, "providers": providers, "editing": True},
    )


@router.post("/api/presets/{preset_id}/edit")
async def update_preset(request: Request, preset_id: int):
    session = require_admin(request)
    form = await request.form()
    data = {k: v for k, v in form.items() if v}
    if "provider_id" in data:
        data["provider_id"] = int(data["provider_id"])
    if "speed" in data:
        data["speed"] = float(data["speed"])
    preset_service.update_preset(preset_id, data)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/presets/{preset_id}/delete")
async def delete_preset(request: Request, preset_id: int):
    session = require_admin(request)
    preset_service.delete_preset(preset_id)
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/presets/{preset_id}/set-default")
async def set_default_preset(request: Request, preset_id: int):
    session = require_admin(request)
    preset = preset_service.get_preset(preset_id)
    if preset:
        preset_service.set_default_preset_name(preset["name"])
    return RedirectResponse(url="/admin/setup", status_code=303)


@router.post("/api/presets/{preset_id}/toggle")
async def toggle_preset(request: Request, preset_id: int):
    session = require_admin(request)
    preset = preset_service.get_preset(preset_id)
    if preset:
        preset_service.update_preset(
            preset_id, {"enabled": 0 if preset["enabled"] else 1}
        )
    return RedirectResponse(url="/admin/setup", status_code=303)


# ---- Integration Page ----

@router.get("/integration")
async def integration_page(request: Request):
    session = require_admin(request)
    presets = preset_service.get_enabled_presets()
    cache_stats = cache_service.get_cache_stats(config.CACHE_DIR)
    return _render(
        "integration.html",
        {

            "presets": presets,
            "cache_stats": cache_stats,
        },
    )


# ---- Logs Page ----

@router.get("/logs")
async def logs_page(request: Request):
    session = require_admin(request)
    logs = log_service.get_recent_logs(limit=50)
    cache_stats = cache_service.get_cache_stats(config.CACHE_DIR)
    return _render(
        "logs.html",
        {

            "logs": logs,
            "cache_stats": cache_stats,
        },
    )


@router.post("/api/cache/clear")
async def clear_cache(request: Request):
    session = require_admin(request)
    cache_service.clear_all_cache(config.CACHE_DIR)
    return RedirectResponse(url="/admin/logs", status_code=303)
