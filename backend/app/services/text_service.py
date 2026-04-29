"""Text normalization for cache key generation."""

import hashlib
import re


def normalize_text(text: str) -> str:
    """Lightweight normalization for cache key consistency.

    - trim leading/trailing whitespace
    - collapse consecutive whitespace to single space
    - preserve Chinese punctuation
    - no semantic rewriting
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def text_hash(text: str) -> str:
    """SHA-256 hash of normalized text, for logging purposes."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:16]


def validate_text_length(raw_text: str, max_length: int) -> tuple[str, int, int]:
    """Validate text length and return normalized text with length info.

    Returns:
        (normalized_text, raw_length, normalized_length)
    Raises:
        ValueError: if normalized text exceeds max_length
    """
    raw_length = len(raw_text)
    normalized = normalize_text(raw_text)
    normalized_length = len(normalized)

    if not normalized:
        raise ValueError("Text is empty after normalization")

    if normalized_length > max_length:
        raise ValueError(
            f"Text too long: {normalized_length} characters (max {max_length})"
        )

    return normalized, raw_length, normalized_length
