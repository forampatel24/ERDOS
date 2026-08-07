"""CRUD operations against the ``historical_disasters`` Chroma collection."""

from __future__ import annotations

import uuid
from typing import Any

from backend.database.chromadb.client import get_collection
from backend.database.chromadb.embeddings import embed_payload


def _disaster_id(disaster: dict[str, Any]) -> str:
    """Return a stable UUID string derived from the disaster payload."""
    canonical = "|".join(
        f"{key}={disaster.get(key)}"
        for key in ("disaster_type", "district_name", "rainfall", "river_level")
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, canonical))


def _metadata(disaster: dict[str, Any]) -> dict[str, Any]:
    """Filter a payload to Chroma-safe primitive metadata values."""
    allowed = {
        "disaster_type",
        "district_name",
        "rainfall",
        "river_level",
        "flood_extent",
        "casualties",
        "response_summary",
    }
    return {key: disaster[key] for key in allowed if key in disaster}


def add_disaster(disaster: dict[str, Any]) -> str:
    """Embed and store a historical disaster record; returns its id."""
    collection = get_collection()
    embedding = embed_payload(disaster)
    doc_id = _disaster_id(disaster)
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[str(disaster.get("response_summary", ""))],
        metadatas=[_metadata(disaster)],
    )
    return doc_id


def search_similars(
    query_embedding: list[float], top_k: int = 5
) -> list[dict[str, Any]]:
    """Return the most similar stored disasters to ``query_embedding``."""
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return [
        {
            "id": doc_id,
            "distance": distance,
            "metadata": metadata or {},
        }
        for doc_id, distance, metadata in zip(ids, distances, metadatas)
    ]


def count() -> int:
    """Return the number of stored historical disaster records."""
    return get_collection().count()
