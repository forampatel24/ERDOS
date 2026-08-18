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


#: Sample historical disaster records used to seed an empty collection so the
#: explainability service can demonstrate similar-disaster retrieval.  Payload
#: fields follow ``DATABASE_SCHEMA.md`` section 9.
SAMPLE_DISASTERS: list[dict[str, Any]] = [
    {
        "disaster_type": "flood",
        "district_name": "Ernakulam",
        "rainfall": 120.5,
        "river_level": 3.8,
        "flood_extent": 0.65,
        "casualties": 2,
        "response_summary": "Severe urban flooding; boats deployed to rescue stranded residents.",
    },
    {
        "disaster_type": "flood",
        "district_name": "Alappuzha",
        "rainfall": 98.0,
        "river_level": 3.2,
        "flood_extent": 0.5,
        "casualties": 0,
        "response_summary": "Low-lying areas inundated; shelters opened for affected families.",
    },
    {
        "disaster_type": "flood",
        "district_name": "Thrissur",
        "rainfall": 145.0,
        "river_level": 4.1,
        "flood_extent": 0.72,
        "casualties": 4,
        "response_summary": "River overflow closed several roads; evacuation routes established.",
    },
    {
        "disaster_type": "flood",
        "district_name": "Pathanamthitta",
        "rainfall": 88.5,
        "river_level": 2.9,
        "flood_extent": 0.38,
        "casualties": 0,
        "response_summary": "Moderate flooding near riverbanks; advisories issued to residents.",
    },
    {
        "disaster_type": "landslide",
        "district_name": "Wayanad",
        "rainfall": 160.0,
        "river_level": 1.5,
        "flood_extent": 0.0,
        "casualties": 8,
        "response_summary": "Hillslope failure after heavy rain; road closure and debris clearance.",
    },
]


def seed_historical_disasters() -> int:
    """Add :data:`SAMPLE_DISASTERS` to the collection when it is empty.

    Returns the number of records added (``0`` when the collection already has
    records, so repeated startup calls are idempotent).
    """
    collection = get_collection()
    if collection.count() > 0:
        return 0
    for disaster in SAMPLE_DISASTERS:
        add_disaster(disaster)
    return len(SAMPLE_DISASTERS)
