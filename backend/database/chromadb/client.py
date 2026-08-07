"""ChromaDB client initialization.

Chromadb is imported lazily so that importing this module never fails when
Chromadb is not installed.
"""

from __future__ import annotations

from typing import Any

from backend.utils.settings import settings
from config.constants import HISTORICAL_DISASTERS_COLLECTION


def get_chroma_client() -> Any:
    """Return a ChromaDB persistent client backed by ``CHROMADB_PATH``."""
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "Chromadb is required for the vector store. "
            "Install it with `pip install chromadb`."
        ) from exc
    return chromadb.PersistentClient(path=settings.chromadb_path)


def get_collection() -> Any:
    """Return the ``historical_disasters`` collection (created if needed)."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=HISTORICAL_DISASTERS_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )