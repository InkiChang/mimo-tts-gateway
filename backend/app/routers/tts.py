"""TTS endpoints for reading apps."""

import time

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from ..security import require_gateway_token
from ..services import log_service, preset_service, provider_service, text_service, tts_service

router = APIRouter()


@router.get("/tts")
async def get_tts(
    request: Request,
    text: str = Query(..., description="Text to synthesize"),
    token: str = Query(..., description="Gateway token"),
    preset: str = Query("default", description="Preset name"),
):
    token = token or ""
    if token:
        from ..security import verify_gateway_token
        if not verify_gateway_token(token):
            raise HTTPException(status_code=401, detail="Invalid gateway token")

    preset_name = preset or preset_service.get_default_preset_name()

    t0 = time.time()
    try:
        audio = await tts_service.synthesize(preset_name, text)
        elapsed = (time.time() - t0) * 1000

        # Determine content type from preset
        p = preset_service.get_preset_by_name(preset_name)
        fmt = p.get("format", "mp3") if p else "mp3"
        media_type = f"audio/{fmt}" if fmt != "mp3" else "audio/mpeg"

        return Response(content=audio, media_type=media_type)

    except ValueError as e:
        elapsed = (time.time() - t0) * 1000
        log_service.log_request(
            path="/tts",
            preset_name=preset_name,
            raw_text_length=len(text),
            normalized_text_length=0,
            text_hash=text_service.text_hash(text),
            cache_hit=False,
            status_code=400,
            latency_ms=int(elapsed),
            error_type="VALIDATION_ERROR" if "text" in str(e).lower() or "long" in str(e).lower() else "CONFIG_ERROR",
            error_message=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        elapsed = (time.time() - t0) * 1000
        error_type = "AUTH_ERROR" if "auth" in str(e).lower() else "UPSTREAM_ERROR"
        log_service.log_request(
            path="/tts",
            preset_name=preset_name,
            raw_text_length=len(text),
            normalized_text_length=0,
            text_hash=text_service.text_hash(text),
            cache_hit=False,
            status_code=502,
            latency_ms=int(elapsed),
            error_type=error_type,
            error_message=str(e),
        )
        raise HTTPException(status_code=502, detail="Upstream TTS service error")

    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        log_service.log_request(
            path="/tts",
            preset_name=preset_name,
            raw_text_length=len(text),
            normalized_text_length=0,
            text_hash=text_service.text_hash(text),
            cache_hit=False,
            status_code=500,
            latency_ms=int(elapsed),
            error_type="INTERNAL_ERROR",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")
