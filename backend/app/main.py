"""FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import close_db, init_db
from .routers import admin, health, tts

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    close_db()


app = FastAPI(
    title="mimo-tts-gateway",
    version=config.VERSION,
    lifespan=lifespan,
)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(health.router, tags=["health"])
app.include_router(tts.router, tags=["tts"])
app.include_router(admin.router, tags=["admin"])


@app.get("/")
async def root(request: Request):
    from .security import verify_admin_session
    session = request.cookies.get("session")
    if session and verify_admin_session(session):
        return RedirectResponse(url="/admin/setup")
    return RedirectResponse(url="/admin/login")
