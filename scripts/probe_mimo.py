#!/usr/bin/env python3
"""
mimo-tts-gateway API Probe - M0-A
Tests MiMo TTS API endpoints to validate request/response formats.

Usage:
    # From environment variables (create .env with MIMO_BASE_URL etc)
    python scripts/probe_mimo.py

    # From command line arguments
    python scripts/probe_mimo.py \
        --base-url https://api.example.com \
        --endpoint /v1/chat/completions \
        --api-key sk-xxx \
        --model mimo-v2.5-tts \
        --voice 冰糖 \
        --format mp3 \
        --mode chat_completions
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    print("httpx is required. Install with: pip install httpx")
    sys.exit(1)


def load_env(env_path: str = ".env") -> dict:
    """Load configuration from .env file if it exists."""
    config = {}
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                config[key] = value
    return config


def build_chat_completions_request(text: str, model: str, voice: str, style: str, fmt: str) -> dict:
    """Build a Chat Completions Audio request body."""
    messages = []
    if style:
        messages.append({
            "role": "user",
            "content": style,
        })
    messages.append({
        "role": "assistant",
        "content": text,
    })
    body = {
        "model": model,
        "messages": messages,
        "audio": {
            "format": fmt,
            "voice": voice,
        },
    }
    return body


def build_audio_speech_request(text: str, model: str, voice: str, fmt: str, speed: float) -> dict:
    """Build an OpenAI-compatible audio.speech request body."""
    body = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": fmt,
        "speed": speed,
    }
    return body


def parse_base64_audio(data: dict, verbose: bool = False) -> tuple[str | None, str | None]:
    """Try to extract base64 audio from response."""
    try:
        choices = data.get("choices", [])
        if not choices:
            return None, None

        choice = choices[0]
        message = choice.get("message", {})
        audio = message.get("audio", {})
        audio_data = audio.get("data")

        if audio_data:
            return audio_data, "base64_audio_in_choices"

        if verbose:
            print(f"[DEBUG] choices[0] keys: {list(choice.keys())}")
            print(f"[DEBUG] message keys: {list(message.keys())}")
            print(f"[DEBUG] audio keys: {list(audio.keys())}")

    except (KeyError, IndexError, TypeError) as e:
        if verbose:
            print(f"[DEBUG] Failed to parse base64 audio: {e}")

    return None, None


def probe_api(args: argparse.Namespace, env: dict) -> int:
    """Run API probe."""
    base_url = args.base_url or env.get("MIMO_BASE_URL")
    endpoint = args.endpoint or env.get("MIMO_ENDPOINT", "/v1/chat/completions")
    api_key = args.api_key or env.get("MIMO_API_KEY")
    auth_type = args.auth_type or env.get("MIMO_AUTH_TYPE", "bearer")
    auth_header = args.auth_header or env.get("MIMO_AUTH_HEADER", "Authorization")
    model = args.model or env.get("MIMO_MODEL", "mimo-v2.5-tts")
    voice = args.voice or env.get("MIMO_VOICE", "冰糖")
    style = args.style or env.get("MIMO_STYLE", "自然、清晰")
    audio_format = args.format or env.get("MIMO_FORMAT", "mp3")
    speed = args.speed or float(env.get("MIMO_SPEED", "1.0"))
    mode = args.mode or env.get("MIMO_MODE", "chat_completions")
    test_text = args.text or env.get("MIMO_TEXT", "你好，这是 mimo-tts-gateway API 探测测试。")
    output_dir = args.output_dir or env.get("MIMO_OUTPUT_DIR", "data/test_audio")
    timeout = args.timeout or int(env.get("MIMO_TIMEOUT", "60"))
    verbose = args.verbose or env.get("MIMO_VERBOSE", "").lower() in ("1", "true", "yes")

    if not base_url:
        print("[ERROR] base_url is required. Set via --base-url or MIMO_BASE_URL in .env")
        return 1

    if not api_key:
        print("[ERROR] api_key is required. Set via --api-key or MIMO_API_KEY in .env")
        return 1

    url = urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    # Build request
    if mode == "chat_completions":
        body = build_chat_completions_request(test_text, model, voice, style, audio_format)
        request_mode = "chat_completions_audio"
    elif mode == "audio_speech":
        body = build_audio_speech_request(test_text, model, voice, audio_format, speed)
        request_mode = "audio_speech"
    else:
        print(f"[ERROR] Unknown mode: {mode} (use chat_completions or audio_speech)")
        return 1

    # Build headers
    if auth_type == "bearer":
        headers = {"Authorization": f"Bearer {api_key}"}
    elif auth_type == "api_key":
        headers = {auth_header: api_key}
    elif auth_type == "custom":
        headers = {auth_header: api_key}
    else:
        headers = {}

    headers["Content-Type"] = "application/json"

    print("=" * 60)
    print("mimo-tts-gateway API Probe")
    print("=" * 60)
    print(f"URL:       {url}")
    print(f"Auth:      {auth_type} ({auth_header})")
    print(f"Model:     {model}")
    print(f"Voice:     {voice}")
    print(f"Style:     {style}")
    print(f"Format:    {audio_format}")
    print(f"Mode:      {request_mode}")
    print(f"Text:      {test_text}")
    print(f"Timeout:   {timeout}s")
    print("-" * 60)
    print(f"[REQUEST]")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print("-" * 60)

    # Make request
    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers=headers)
        elapsed = (time.time() - start) * 1000
    except httpx.TimeoutException:
        print("[ERROR] Request timed out")
        return 1
    except httpx.ConnectError as e:
        print(f"[ERROR] Connection failed: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return 1

    content_type = resp.headers.get("content-type", "")
    print(f"[RESPONSE] Status: {resp.status_code}")
    print(f"[RESPONSE] Content-Type: {content_type}")
    print(f"[RESPONSE] Latency: {elapsed:.0f}ms")

    # Handle errors
    if resp.status_code >= 400:
        print(f"[RESPONSE] Error body:")
        try:
            error_data = resp.json()
            print(json.dumps(error_data, ensure_ascii=False, indent=2))
        except Exception:
            print(resp.text[:500])
        return 1

    # Try parsing as JSON first
    is_json = "application/json" in content_type

    # Try to parse response
    try:
        response_data = resp.json() if is_json else {}
    except Exception:
        response_data = {}

    # Check if it's binary audio
    is_binary = (
        not is_json
        and ("audio/" in content_type or "application/octet-stream" in content_type)
        and len(resp.content) > 100
    )

    audio_data = None
    response_mode = None

    if is_binary:
        audio_data = resp.content
        response_mode = "binary_audio"
        print(f"[RESPONSE] Binary audio detected ({len(audio_data)} bytes)")
    elif response_data:
        # Try base64 path
        b64, mode_hint = parse_base64_audio(response_data, verbose=verbose)
        if b64:
            try:
                audio_data = base64.b64decode(b64)
                response_mode = mode_hint or "base64_audio_in_choices"
                print(f"[RESPONSE] Base64 audio detected ({len(audio_data)} bytes decoded)")
            except Exception as e:
                print(f"[ERROR] Failed to decode base64: {e}")
        else:
            print(f"[RESPONSE] JSON response (not binary, no base64 audio found)")
            if verbose:
                print(json.dumps(response_data, ensure_ascii=False, indent=2)[:2000])
            else:
                print(json.dumps(response_data, ensure_ascii=False)[:500])

    # Save audio
    if audio_data:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ext = audio_format if audio_format in ("mp3", "wav", "opus", "ogg") else "mp3"
        output_path = Path(output_dir) / f"probe_test.{ext}"
        with open(output_path, "wb") as f:
            f.write(audio_data)
        print(f"[OUTPUT] Audio saved to: {output_path} ({len(audio_data)} bytes)")
    else:
        print("[OUTPUT] No audio data extracted from response")

    # Summary
    print("-" * 60)
    print("[SUMMARY]")
    print(f"  request_mode:   {request_mode}")
    print(f"  response_mode:  {response_mode or 'unknown'}")
    print(f"  status_code:    {resp.status_code}")
    print(f"  latency_ms:     {elapsed:.0f}")
    print(f"  content_type:   {content_type}")
    print(f"  audio_extracted: {'yes' if audio_data else 'no'}")
    print("=" * 60)

    return 0 if audio_data else 1


def main():
    parser = argparse.ArgumentParser(
        description="MiMo TTS API Probe - validate request/response before building gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base-url", help="API base URL")
    parser.add_argument("--endpoint", help="API endpoint path")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--auth-type", choices=["bearer", "api_key", "custom", "none"], help="Auth type")
    parser.add_argument("--auth-header", help="Auth header name")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--voice", help="Voice name")
    parser.add_argument("--style", help="Style description")
    parser.add_argument("--format", choices=["mp3", "wav", "opus", "ogg", "pcm"], help="Audio format")
    parser.add_argument("--speed", type=float, help="Speech speed")
    parser.add_argument("--mode", choices=["chat_completions", "audio_speech"], help="Request mode")
    parser.add_argument("--text", help="Test text to synthesize")
    parser.add_argument("--timeout", type=int, help="Request timeout seconds")
    parser.add_argument("--output-dir", help="Output directory for audio")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    env = load_env(Path(__file__).resolve().parent.parent / ".env")

    return probe_api(args, env)


if __name__ == "__main__":
    sys.exit(main())
