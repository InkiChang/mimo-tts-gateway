# mimo-tts-gateway

A self-hosted TTS gateway designed for reading apps like Legado/Yuedu (阅读).

mimo-tts-gateway lets you connect MiMo TTS compatible APIs to reading apps through a stable local gateway. It protects your upstream API keys, supports official and third-party relay APIs, caches generated audio, and provides a simple WebUI for configuring base_url, api_key, model, voice and presets.

## Features

- Reading app compatible `/tts` endpoint
- WebUI provider configuration
- Official MiMo API and third-party relay API support
- Audio cache to avoid repeated synthesis
- API key protection
- Token authentication
- Docker/NAS friendly deployment
- Preset system for default/sleep/fast/drama reading modes

## Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USER/mimo-tts-gateway.git
cd mimo-tts-gateway
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set:
- `GATEWAY_TOKEN` - token for reading app access
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` - WebUI login
- `SESSION_SECRET` - random string for session encryption

### 3. Start

```bash
docker compose up -d
```

### 4. Setup

1. Open `http://YOUR_NAS_IP:8000` in a browser
2. Login with admin credentials
3. Add a Provider (base_url, api_key, model, voice)
4. Add a Preset (name, provider, voice, style, format, speed)
5. Click "Test Pronunciation" to verify
6. Copy the TTS URL to your reading app

### 5. Reading App Config

In Legado/阅读/Yuedu, add a TTS source:

```
http://YOUR_NAS_IP:8000/tts?token=YOUR_GATEWAY_TOKEN&preset=default&text={{speakText}}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Listen address |
| `APP_PORT` | `8000` | Listen port |
| `ADMIN_USERNAME` | `admin` | WebUI admin username |
| `ADMIN_PASSWORD` | `change-me` | WebUI admin password |
| `SESSION_SECRET` | `change-me-session-secret` | Session encryption key |
| `GATEWAY_TOKEN` | `change-me` | Token for reading app access |
| `DATA_DIR` | `/data` | Persistent data directory |
| `CACHE_DIR` | `/data/cache` | Audio cache directory |
| `MAX_TEXT_LENGTH` | `1000` | Max text characters per request |
| `MAX_CONCURRENT_SYNTHESIS` | `2` | Max concurrent upstream calls |
| `DEFAULT_TIMEOUT_SECONDS` | `60` | Upstream request timeout |

## Security

- Never expose port 8000 directly to the public internet
- Use Tailscale, WireGuard, or Cloudflare Tunnel for remote access
- The gateway token should be kept secret
- Upstream API keys are stored in the SQLite database on disk
- Session cookies are HTTP-only

## License

MIT
