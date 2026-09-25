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
    """Return the ``historical_disasters`` collection (created if needed).

    Uses tuned HNSW params (M=16, efConstruction=200, efSearch=100) for
    better recall/latency at the ERDOS scale (~5K records, 256-dim).  See
    ``backend.optimization.chroma_tuning.TUNED_HNSW_CONFIG``.  Existing
    collections retain their original params — delete ``data/chromadb`` to
    re-create with new tuning.
    """
    client = get_chroma_client()
    try:
        from backend.optimization.chroma_tuning import get_tuned_hnsw_config

        hnsw_meta = get_tuned_hnsw_config()
    except Exception:
        hnsw_meta = {"hnsw:space": "cosine"}
    return client.get_or_create_collection(
        name=HISTORICAL_DISASTERS_COLLECTION,
        metadata=hnsw_meta,
    )