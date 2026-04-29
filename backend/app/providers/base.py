"""Base class for TTS provider adapters."""

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    @abstractmethod
    def build_request(self, text: str, provider: dict) -> dict:
        pass

    @abstractmethod
    def parse_response(self, response_data: dict, response_bytes: bytes, content_type: str, provider: dict) -> bytes:
        pass
