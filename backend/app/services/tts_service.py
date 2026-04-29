"""Core TTS service orchestrating preset, provider, cache, and upstream calls."""

import asyncio
import json
import time
from urllib.parse import urljoin

import httpx

from .. import config
from . import cache_service, log_service, preset_service, provider_service, text_service
from ..providers.base import BaseAdapter
from ..providers.chat_completions_audio import ChatCompletionsAudioAdapter


ADAPTERS: dict[str, BaseAdapter] = {
    "chat_completions_audio": ChatCompletionsAudioAdapter(),
}

synthesis_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_SYNTHESIS)


def get_adapter(request_mode: str) -> BaseAdapter:
    adapter = ADAPTERS.get(request_mode)
    if not adapter:
        raise ValueError(f"Unsupported request_mode: {request_mode}")
    return adapter


def resolve_preset_and_provider(preset_name: str) -> tuple[dict, dict]:
    """Resolve preset and its associated provider.

    Returns:
        (preset, provider)
    Raises:
        ValueError: if preset or provider not found
    """
    preset = preset_service.get_preset_by_name(preset_name)
    if not preset:
        raise ValueError(f"Preset not found or disabled: {preset_name}")

    provider = provider_service.get_provider(preset["provider_id"])
    if not provider:
        raise ValueError(f"Provider not found: {preset['provider_id']}")
    if not provider.get("enabled"):
        raise ValueError(f"Provider disabled: {provider['name']}")

    return preset, provider


async def synthesize(preset_name: str, text: str) -> bytes:
    """Main synthesis flow.

    Args:
        preset_name: Name of the preset
        text: Text to synthesize

    Returns:
        Audio bytes

    Raises:
        ValueError: on config or validation errors
        RuntimeError: on upstream errors
    """
    preset, provider = resolve_preset_and_provider(preset_name)

    normalized, raw_len, norm_len = text_service.validate_text_length(
        text, config.MAX_TEXT_LENGTH
    )

    voice = preset.get("voice") or provider.get("default_voice", "")
    style = preset.get("style", "")
    fmt = preset.get("format") or provider.get("output_format", "mp3")
    speed = preset.get("speed", 1.0)
    text_prefix = preset.get("text_prefix") or ""
    text_suffix = preset.get("text_suffix") or ""
    effective_text = f"{text_prefix}{normalized}{text_suffix}"
    request_mode = provider.get("request_mode", "chat_completions_audio")
    response_mode = provider.get("response_mode", "base64_audio_in_choices")

    text_hash_val = text_service.text_hash(text)

    cache_key = cache_service.compute_cache_key(
        provider_id=provider["id"],
        provider_base_url=provider["base_url"],
        request_mode=request_mode,
        response_mode=response_mode,
        model=provider["model"],
        voice=voice,
        style=style,
        text=effective_text,
        fmt=fmt,
        speed=speed,
        text_prefix=text_prefix,
        text_suffix=text_suffix,
    )

    # Check cache
    cached = cache_service.check_cache(cache_key, config.CACHE_DIR)
    if cached:
        start_time = time.time()
        with open(cached["file_path"], "rb") as f:
            audio = f.read()
        elapsed = (time.time() - start_time) * 1000

        log_service.log_request(
            path="/tts",
            provider_id=provider["id"],
            preset_name=preset_name,
            raw_text_length=raw_len,
            normalized_text_length=norm_len,
            text_hash=text_hash_val,
            cache_hit=True,
            status_code=200,
            latency_ms=int(elapsed),
        )
        return audio

    # Handle in-flight merge
    lock = cache_service.in_flight.get(cache_key)
    if lock is None:
        lock = asyncio.Lock()
        cache_service.in_flight[cache_key] = lock

    async with lock:
        # Double-check cache after acquiring lock
        cached = cache_service.check_cache(cache_key, config.CACHE_DIR)
        if cached:
            start_time = time.time()
            with open(cached["file_path"], "rb") as f:
                audio = f.read()
            elapsed = (time.time() - start_time) * 1000
            log_service.log_request(
                path="/tts",
                provider_id=provider["id"],
                preset_name=preset_name,
                raw_text_length=raw_len,
                normalized_text_length=norm_len,
                text_hash=text_hash_val,
                cache_hit=True,
                status_code=200,
                latency_ms=int(elapsed),
            )
            return audio

        try:
            adapter = get_adapter(request_mode)
            provider_with_style = {
                **provider,
                "_preset_style": style,
                "default_voice": voice,
                "output_format": fmt,
            }
            request_body = adapter.build_request(effective_text, provider_with_style)

            async with synthesis_semaphore:
                audio = await _call_upstream(provider, request_body, adapter)

            cache_service.save_cache(
                cache_key=cache_key,
                provider_id=provider["id"],
                model=provider["model"],
                voice=voice,
                text_hash=text_hash_val,
                style=style,
                fmt=fmt,
                audio_data=audio,
                cache_root=config.CACHE_DIR,
            )

            return audio

        finally:
            cache_service.in_flight.pop(cache_key, None)


async def _call_upstream(
    provider: dict,
    request_body: dict,
    adapter: BaseAdapter,
) -> bytes:
    """Call upstream TTS API and parse the response."""
    base_url = provider["base_url"].rstrip("/")
    endpoint = provider.get("endpoint", "/v1/chat/completions")
    url = urljoin(base_url + "/", endpoint.lstrip("/"))

    auth_type = provider.get("auth_type", "bearer")
    auth_header = provider.get("auth_header_name", "Authorization")
    api_key = provider.get("api_key", "")
    timeout = provider.get("timeout_seconds", config.DEFAULT_TIMEOUT_SECONDS)
    retry_count = provider.get("retry_count", config.DEFAULT_RETRY_COUNT)

    headers = {"Content-Type": "application/json"}
    if api_key:
        if auth_type == "bearer":
            headers[auth_header] = f"Bearer {api_key}"
        elif auth_type in ("api_key", "custom"):
            headers[auth_header] = api_key

    last_error = None
    for attempt in range(retry_count + 1):
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=request_body, headers=headers)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 401 or resp.status_code == 403:
                raise RuntimeError(f"Upstream auth failed: {resp.status_code}")

            if resp.status_code == 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text[:200]
                raise ValueError(f"Upstream returned 400: {detail}")

            if resp.status_code == 429:
                await asyncio.sleep(2 * (attempt + 1))
                continue

            if resp.status_code >= 500:
                if attempt < retry_count:
                    await asyncio.sleep(1)
                    continue
                raise RuntimeError(f"Upstream error after {retry_count + 1} attempts: {resp.status_code}")

            content_type = resp.headers.get("content-type", "")

            try:
                response_data = resp.json() if "application/json" in content_type else {}
            except Exception:
                response_data = {}

            audio = adapter.parse_response(
                response_data=response_data,
                response_bytes=resp.content,
                content_type=content_type,
                provider=provider,
            )
            return audio

        except httpx.TimeoutException:
            last_error = RuntimeError("Upstream timeout")
            if attempt < retry_count:
                continue

        except httpx.ConnectError as e:
            last_error = RuntimeError(f"Cannot connect to upstream: {e}")
            if attempt < retry_count:
                await asyncio.sleep(1)
                continue

    raise last_error or RuntimeError("Upstream request failed")


async def test_synthesis(provider: dict, voice: str, style: str, fmt: str, text: str) -> dict:
    """Test synthesis for a provider. Returns dict with success, latency_ms, audio_url."""
    normalized, _, _ = text_service.validate_text_length(text, 200)
    request_mode = provider.get("request_mode", "chat_completions_audio")
    adapter = get_adapter(request_mode)

    effective_voice = voice or provider.get("default_voice", "")
    effective_fmt = fmt or provider.get("output_format", "mp3")

    provider_with_style = {
        **provider,
        "_preset_style": style,
        "default_voice": effective_voice,
        "output_format": effective_fmt,
    }

    request_body = adapter.build_request(normalized, provider_with_style)

    start = time.time()
    async with synthesis_semaphore:
        audio = await _call_upstream(provider_with_style, request_body, adapter)
    elapsed = (time.time() - start) * 1000

    # Cache test results too, using simple cache key
    cache_key = cache_service.compute_cache_key(
        provider_id=provider["id"],
        provider_base_url=provider["base_url"],
        request_mode=request_mode,
        response_mode=provider.get("response_mode", "base64_audio_in_choices"),
        model=provider["model"],
        voice=effective_voice,
        style=style,
        text=normalized,
        fmt=effective_fmt,
        speed=1.0,
    )

    cached = cache_service.check_cache(cache_key, config.CACHE_DIR)
    if not cached:
        cache_service.save_cache(
            cache_key=cache_key,
            provider_id=provider["id"],
            model=provider["model"],
            voice=effective_voice,
            text_hash=text_service.text_hash(text),
            style=style,
            fmt=effective_fmt,
            audio_data=audio,
            cache_root=config.CACHE_DIR,
        )

    return {
        "success": True,
        "latency_ms": int(elapsed),
        "audio_url": f"/admin/api/test-audio/{cache_key}.{effective_fmt}",
        "cache_hit": bool(cached),
    }
