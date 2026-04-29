# Provider Configuration Guide

## Verified Providers

### Relay API (fufu.iqach.top)

**Status**: Verified (2026-04-29)

| Field | Value |
|-------|-------|
| Provider Name | Fufu Relay |
| Provider Type | mimo_chat_completions |
| Base URL | https://fufu.iqach.top |
| Endpoint | /v1/chat/completions |
| Auth Type | bearer |
| Auth Header Name | Authorization |
| API Key | free |
| Model | mimo-v2.5-tts |
| Voice | 冰糖 |
| Output Format | mp3 |
| Request Mode | chat_completions_audio |
| Response Mode | base64_audio_in_choices |
| Timeout Seconds | 60 |
| Retry Count | 1 |

**Probe Results**:
- Status: 200 OK
- Content-Type: application/json
- Audio extraction: base64 from `choices[0].message.audio.data`
- Latency: ~2-4 seconds per request
- Text must be in `assistant` message
- Style (optional) goes in `user` message
- Auth also works without any header (no auth required)

**Example Request**:

```json
{
    "model": "mimo-v2.5-tts",
    "messages": [
        {"role": "user", "content": "自然、清晰"},
        {"role": "assistant", "content": "你好，这是测试文本。"}
    ],
    "audio": {
        "format": "mp3",
        "voice": "冰糖"
    }
}
```

**Example Response** (structure, audio data truncated):

```json
{
    "id": "...",
    "model": "mimo-v2.5-tts",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "",
                "audio": {
                    "id": "...",
                    "data": "//OExAAAAAAA...",
                    "expires_at": null,
                    "transcript": null
                }
            },
            "finish_reason": "stop"
        }
    ],
    "usage": { ... }
}
```

## Official MiMo API (Pending)

The official MiMo API has not been verified yet. Will be tested in M0-B phase.

### Expected Configuration (unverified)

| Field | Expected Value |
|-------|---------------|
| Base URL | https://api.xiaomimimo.com |
| Endpoint | /v1/chat/completions |
| Auth Type | api_key (header: api-key) |
| Model | mimo-v2.5-tts |
| Voice | 冰糖 |
| Output Format | mp3 |

See [Xiaomi MiMo API docs](https://platform.xiaomimimo.com/docs/usage-guide/speech-synthesis-v2.5)
