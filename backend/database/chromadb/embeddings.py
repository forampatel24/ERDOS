"""Deterministic embedding generation for historical disasters.

Uses a pure-Python character n-gram hashing vectorizer (no ML model). The
mapping from n-gram to vector index relies on CRC32 so embeddings are stable
across processes and machines.
"""

from __future__ import annotations

import math
import zlib
from typing import Any

from backend.utils.validation import coerce_float

EMBEDDING_DIM = 256
NGRAM_SIZES = (2, 3, 4)

_PAYLOAD_TEXT_KEYS = ("disaster_type", "district_name", "response_summary")
_PAYLOAD_NUMERIC_KEYS = ("rainfall", "river_level", "flood_extent", "casualties")


def _iter_ngrams(text: str):
    """Yield character n-grams of the configured sizes."""
    lowered = text.lower()
    for size in NGRAM_SIZES:
        for index in range(len(lowered) - size + 1):
            yield lowered[index : index + size]


def _deterministic_index(token: str) -> int:
    """Map a token to a stable vector index via CRC32."""
    return zlib.crc32(token.encode("utf-8")) % EMBEDDING_DIM


def generate_embedding(text: str) -> list[float]:
    """Return a deterministic L2-normalized vector for ``text``."""
    vector = [0.0] * EMBEDDING_DIM
    for token in _iter_ngrams(text):
        vector[_deterministic_index(token)] += 1.0

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _payload_text(payload: dict[str, Any]) -> str:
    """Flatten a disaster payload into a canonical text representation."""
    text_parts = [
        str(payload.get(key, "")) for key in _PAYLOAD_TEXT_KEYS if payload.get(key)
    ]
    numeric_parts = [
        f"{key}={coerce_float(payload.get(key, 0.0), 0.0):.2f}"
        for key in _PAYLOAD_NUMERIC_KEYS
    ]
    return " ".join([*text_parts, *numeric_parts]).strip()


def embed_payload(payload: dict[str, Any]) -> list[float]:
    """Vectorize a disaster payload into a fixed-size embedding."""
    return generate_embedding(_payload_text(payload))
