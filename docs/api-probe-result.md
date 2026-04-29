# M0-A API Probe Result

> Date: 2026-04-29
> Target: Fufu Relay API (第三方中转)
> Status: SUCCESS

## Summary

The relay API at `https://fufu.iqach.top` was successfully probed and confirmed working. The API uses the standard Chat Completions Audio protocol compatible with MiMo-V2.5-TTS.

## Confirmed Details

### Authentication

- Auth type: Bearer token
- Header: `Authorization: Bearer free`
- Also works with: `api-key: free`
- Also works with: No auth at all (none)

### Request Format

- Method: POST
- Content-Type: application/json
- Endpoint: `/v1/chat/completions`
- Text goes in: `messages[assistant].content`
- Style goes in: `messages[user].content` (optional)

### Response Format

- Content-Type: `application/json`
- Audio encoding: Base64
- Audio field path: `choices[0].message.audio.data`
- Response mode: `base64_audio_in_choices`
- No binary audio response mode detected (always JSON)
- No audio_url response mode detected

### Supported Parameters

- Model: `mimo-v2.5-tts`
- Voice: `冰糖` (confirmed working)
- Format: `mp3` (confirmed, likely also supports wav)
- Style: Sent as user message, appears effective
- Speed: Not tested (Chat Completions Audio may not support speed directly)

### Performance

- Latency: 2-4 seconds per short text (~10 chars)
- Audio size: ~24-32KB per short text snippet
- Error handling: Returns JSON error responses (not tested exhaustively)

## First Default Provider Configuration

Based on the probe results, the first v0.1 default Provider should be configured as:

```yaml
provider_type: mimo_chat_completions
base_url: https://fufu.iqach.top
endpoint: /v1/chat/completions
auth_type: bearer
auth_header_name: Authorization
api_key: free
model: mimo-v2.5-tts
default_voice: 冰糖
request_mode: chat_completions_audio
response_mode: base64_audio_in_choices
output_format: mp3
timeout_seconds: 60
retry_count: 1
```

## Next Steps

1. ✅ M0-A complete - Relay API verified
2. ⏳ M0-B - Official MiMo API probe (if credentials available)
3. ⏳ M1 - Headless Gateway implementation
4. ⏳ M2 - WebUI
5. ⏳ M3 - Docker + GitHub Ready
