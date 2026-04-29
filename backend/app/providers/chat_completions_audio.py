"""Chat Completions Audio adapter for MiMo TTS and compatible APIs."""

import base64
import json

from .base import BaseAdapter


class ChatCompletionsAudioAdapter(BaseAdapter):
    def build_request(self, text: str, provider: dict) -> dict:
        """Build Chat Completions request body.

        Args:
            text: The normalized text to synthesize
            provider: Provider config dict with voice, style, etc.

        Returns:
            Dict ready for JSON serialization
        """
        voice = provider.get("default_voice", "")
        fmt = provider.get("output_format", "mp3")
        model = provider.get("model", "")
        style = provider.get("_preset_style", "")

        messages = []
        if style:
            messages.append({"role": "user", "content": style})
        messages.append({"role": "assistant", "content": text})

        body = {
            "model": model,
            "messages": messages,
            "audio": {
                "format": fmt,
                "voice": voice,
            },
        }
        return body

    def parse_response(
        self,
        response_data: dict,
        response_bytes: bytes,
        content_type: str,
        provider: dict,
    ) -> bytes:
        """Extract audio bytes from Chat Completions response.

        Supports:
        - base64_audio_in_choices: audio data in choices[0].message.audio.data
        - binary_audio: upstream returns raw audio bytes directly
        """
        response_mode = provider.get("response_mode", "base64_audio_in_choices")

        if response_mode == "base64_audio_in_choices" or (
            "application/json" in content_type and not response_mode
        ):
            return self._parse_base64(response_data)

        if response_mode == "binary_audio" or (
            "audio/" in content_type and len(response_bytes) > 100
        ):
            return self._parse_binary(response_bytes, content_type)

        # Fallback: try base64 first, then binary
        if response_data:
            result = self._parse_base64(response_data)
            if result:
                return result

        if len(response_bytes) > 100:
            return response_bytes

        raise ValueError(f"Could not extract audio from response (content-type: {content_type})")

    def _parse_base64(self, data: dict) -> bytes:
        """Extract base64 audio from choices[0].message.audio.data."""
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices in response")

        choice = choices[0]
        message = choice.get("message", {})
        audio = message.get("audio", {})
        audio_data = audio.get("data")

        if isinstance(audio_data, dict):
            audio_data = audio_data.get("data") or audio_data.get("audio")

        if not audio_data:
            raise ValueError(
                f"Base64 audio not found in response at choices[0].message.audio.data"
            )

        try:
            return base64.b64decode(audio_data)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 audio: {e}")

    def _parse_binary(self, response_bytes: bytes, content_type: str) -> bytes:
        """Return raw binary audio."""
        if len(response_bytes) < 100:
            raise ValueError(f"Binary audio too small: {len(response_bytes)} bytes")
        return response_bytes
