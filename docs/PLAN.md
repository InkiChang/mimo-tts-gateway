# mimo-tts-gateway Plan

Source planning document:

`/home/inkichang/.openclaw/share-vault/项目/PROJECT_PLAN_mimo_tts_gateway.md`

## Positioning

`mimo-tts-gateway` is a self-hosted TTS gateway for reading apps. It should support official MiMo TTS APIs and third-party relay APIs through configurable providers, presets, caching, token authentication, and Docker/NAS-friendly deployment.

## v0.1 Scope

Must have:

- Docker / Docker Compose deployment
- Admin login
- WebUI provider configuration
- WebUI preset configuration
- `GET /tts` for reading apps
- `POST /v1/tts` for programmatic use
- Official MiMo-compatible API support
- Third-party relay API support
- Custom `base_url`, `endpoint`, `api_key`, `model`, `voice`
- Request mode configuration
- Response mode configuration
- Audio cache
- Gateway token authentication
- Provider test synthesis
- Reading app URL generation
- Basic request logs
- Health check

Explicitly out of scope for v0.1:

- Batch synthesis
- Chapter/book synthesis
- Audiobook export
- Voice clone
- Voice design
- Multi-character narration
- Complex job queue
- Audiobookshelf/Jellyfin integration
- Multi-user/multi-tenant system
- Public commercial service

## Architecture

```text
Reading app / TTS client
        ↓
GET /tts or POST /v1/tts
        ↓
mimo-tts-gateway
        ↓
Auth layer: token / admin session
        ↓
Config layer: Provider / Preset
        ↓
Text layer: trim, normalize, max length
        ↓
Cache layer: return audio on cache hit
        ↓
Adapter layer: official or relay API request
        ↓
Upstream API: MiMo official / relay / OpenAI-compatible endpoint
        ↓
Response parser: base64 audio / binary audio / audio_url
        ↓
Cache audio and return audio/*
```

## Planned Directory Structure

```text
mimo-tts-gateway/
  README.md
  LICENSE
  Dockerfile
  docker-compose.yml
  .env.example
  .gitignore

  backend/
    requirements.txt
    app/
      main.py
      config.py
      database.py
      security.py
      routers/
      providers/
      services/
      models/
      templates/
      static/

  data/
    gateway.sqlite
    cache/

  docs/
    PLAN.md
    deployment.md
    yuedu.md
    provider-config.md
    api.md
    troubleshooting.md
    roadmap.md
```

## Core Concepts

Provider fields:

- `name`
- `enabled`
- `base_url`
- `endpoint`
- `api_key`
- `auth_type`
- `auth_header_name`
- `model`
- `default_voice`
- `request_mode`
- `response_mode`
- `output_format`
- `timeout_seconds`
- `retry_count`

Preset fields:

- `name`
- `provider_id`
- `voice`
- `style`
- `format`
- `speed`
- `text_prefix`
- `text_suffix`
- `enabled`

## API Plan

Health check:

```http
GET /health
```

Reading app endpoint:

```http
GET /tts?token=xxx&preset=default&text=你好
```

Programmatic endpoint:

```http
POST /v1/tts
Authorization: Bearer <gateway-token>
Content-Type: application/json
```

Provider test endpoint:

```http
POST /admin/api/providers/{provider_id}/test
```

## Upstream Request Modes

v0.1 supports:

- `chat_completions_audio` for MiMo-V2.5-TTS style APIs
- `audio_speech` for OpenAI audio speech compatible APIs

Future support:

- `custom_json_template`
- `custom_form_template`

## Response Modes

v0.1 should support at least:

- base64 audio in choices
- binary audio response

`audio_url` parsing can be added if the implementation remains small.

## Security

- Upstream API keys must stay server-side.
- Reading apps only receive `GATEWAY_TOKEN`.
- v0.1 uses a single global gateway token.
- Admin login uses `ADMIN_USERNAME` and `ADMIN_PASSWORD` from env/config.
- Do not recommend exposing port `8000` directly to the public internet.
- v0.1 does not implement CSRF protection for admin form posts. Keep the WebUI LAN/VPN-only.
- Future hardening should add CSRF tokens or same-origin custom headers for all admin mutations.
- Default `ADMIN_PASSWORD`, `GATEWAY_TOKEN`, and `SESSION_SECRET` are for testing only. Users should modify them in `.env` before regular use.

## v0.1 Milestones

1. Scaffold FastAPI backend, config, database initialization, and health check.
2. Add SQLite schema and repository/service layer for providers, presets, cache, and logs.
3. Implement gateway auth and admin session login.
4. Implement provider and preset CRUD APIs/pages.
5. Implement text normalization and cache key generation.
6. Implement `GET /tts` and `POST /v1/tts` using presets and overrides.
7. Implement `chat_completions_audio` and `audio_speech` adapters.
8. Implement base64 and binary audio response parsing.
9. Add file cache and request logging.
10. Add WebUI dashboard, provider page, preset page, integration URL page, cache/log pages.
11. Add Dockerfile, docker-compose.yml, `.env.example`, and quick-start docs.
12. Verify Docker Compose startup, WebUI login, provider test audio, cache hit, and reading URL audio response.

## Future Hardening

- Add CSRF protection for `/admin/api/*` mutation endpoints.
- Warn or fail startup when production runs with default `ADMIN_PASSWORD`, `GATEWAY_TOKEN`, or `SESSION_SECRET`.
- Support HTTPS-aware secure cookies behind reverse proxies.
- Add provider delete safeguards when presets still reference the provider.

## GitHub Readiness

Before first push:

- Confirm repo name: `mimo-tts-gateway`.
- Add `LICENSE` if the project will be public.
- Keep `.env`, `data/`, cache files, and real API keys out of git.
- Commit planning scaffold separately from implementation.
- Create GitHub remote and push `main` only when ready.
