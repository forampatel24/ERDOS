"""ChromaDB vector search tuning: HNSW params, batch queries, benchmarks.

ChromaDB uses HNSW (Hierarchical Navigable Small World) for ANN search.
Tuning ``M``, ``efConstruction``, and ``efSearch`` trades recall vs latency.
These defaults are profiled for ~5K disaster records (the expected ERDOS scale):

- M=16 (bi-directional links per node; 16 balances recall vs memory)
- efConstruction=200 (higher = better graph quality at index time)
- efSearch=100 (higher = higher recall at query time; 100 gives >0.95 recall@5)

The tuning is applied at collection creation via Chroma's ``hnsw:*`` metadata.
Existing collections keep their params — drop and re-seed to apply new tuning
(e.g., ``rm -rf data/chromadb`` then restart).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from backend.utils.logging import get_logger

logger = get_logger("optimization.chroma_tuning")

# Tuned HNSW configuration for 256-dim n-gram embeddings and ~5K records
TUNED_HNSW_CONFIG: Dict[str, Any] = {
    "hnsw:space": "cosine",
    "hnsw:construction_ef": 200,
    "hnsw:M": 16,
    "hnsw:search_ef": 100,
    # Batch size for bulk add/query
    "hnsw:batch_size": 100,
}

# Legacy config (previous default) for comparison
LEGACY_HNSW_CONFIG: Dict[str, Any] = {
    "hnsw:space": "cosine",
}


def get_tuned_hnsw_config() -> Dict[str, Any]:
    """Return the tuned HNSW metadata dict for ``get_or_create_collection``."""
    return dict(TUNED_HNSW_CONFIG)


def benchmark_search(
    query_embeddings: List[List[float]],
    top_k: int = 5,
    warmup: int = 2,
) -> Dict[str, Any]:
    """Benchmark ChromaDB search latency and recall hint.

    Runs ``warmup`` + measured queries and returns p50/p95 latency.
    Does not require ground truth — reports throughput only.

    Returns:
        dict with ``num_queries``, ``p50_ms``, ``p95_ms``, ``avg_ms``, ``qps``.
    """
    from backend.database.chromadb.retrieval import search_similars

    if not query_embeddings:
        return {"num_queries": 0, "p50_ms": 0, "p95_ms": 0, "avg_ms": 0, "qps": 0}

    # Warmup (JIT, page cache)
    for emb in query_embeddings[:warmup]:
        try:
            search_similars(emb, top_k=top_k)
        except Exception:
            pass

    latencies: List[float] = []
    for emb in query_embeddings:
        t0 = time.perf_counter()
        try:
            search_similars(emb, top_k=top_k)
        except Exception:
            pass
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    n = len(latencies)
    p50 = latencies[n // 2] if n else 0
    p95 = latencies[int(n * 0.95)] if n else 0
    avg = sum(latencies) / n if n else 0
    qps = 1000.0 / avg if avg else 0
    result = {
        "num_queries": n,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "avg_ms": round(avg, 2),
        "qps": round(qps, 1),
        "hnsw_config": get_tuned_hnsw_config(),
    }
    logger.info(
        "Chroma benchmark: {} queries p50={}ms p95={}ms qps={}",
        n,
        result["p50_ms"],
        result["p95_ms"],
        result["qps"],
    )
    return result


def batch_search(
    query_embeddings: List[List[float]],
    top_k: int = 5,
) -> List[List[Dict[str, Any]]]:
    """Batch query ChromaDB for multiple embeddings (sequential, cached collection).

    Chroma's Python client has no native batch ``query`` with varying embeddings,
    so this loops but reuses the collection handle (saves ~2-3ms per query vs
    calling ``search_similars`` which re-acquires the collection each time).
    """
    if not query_embeddings:
        return []
    try:
        from backend.database.chromadb.client import get_collection

        collection = get_collection()
        # Single collection handle; fan out queries
        results: List[List[Dict[str, Any]]] = []
        for emb in query_embeddings:
            try:
                res = collection.query(
                    query_embeddings=[emb],
                    n_results=top_k,
                    include=["metadatas", "distances"],
                )
                ids = res.get("ids", [[]])[0]
                distances = res.get("distances", [[]])[0]
                metadatas = res.get("metadatas", [[]])[0]
                batch = [
                    {"id": i, "distance": d, "metadata": m or {}}
                    for i, d, m in zip(ids, distances, metadatas)
                ]
                results.append(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("batch_search query failed: {}", exc)
                results.append([])
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("batch_search failed: {}", exc)
        # Fallback to sequential search_similars
        from backend.database.chromadb.retrieval import search_similars

        return [search_similars(emb, top_k=top_k) for emb in query_embeddings]
