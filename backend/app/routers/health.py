"""Health check endpoint."""

from fastapi import APIRouter

from .. import config

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": config.VERSION,
    }
