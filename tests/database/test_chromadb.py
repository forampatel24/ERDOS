"""Tests for ChromaDB layer: embeddings, retrieval, client, tuning."""

from __future__ import annotations

import pytest

from backend.database.chromadb.embeddings import (
    generate_embedding,
    embed_payload,
    EMBEDDING_DIM,
)
from backend.database.chromadb.retrieval import (
    SAMPLE_DISASTERS,
    add_disaster,
    search_similars,
    count,
    seed_historical_disasters,
)


class TestEmbeddings:
    def test_generate_embedding_dim(self):
        v = generate_embedding("flood in Ernakulam heavy rain")
        assert len(v) == EMBEDDING_DIM
        # L2 normalized
        import math

        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-6

    def test_deterministic(self):
        a = generate_embedding("same text")
        b = generate_embedding("same text")
        assert a == b

    def test_different_texts_differ(self):
        a = generate_embedding("flood")
        b = generate_embedding("landslide")
        assert a != b

    def test_embed_payload(self):
        payload = {
            "disaster_type": "flood",
            "district_name": "Ernakulam",
            "rainfall": 120.0,
            "river_level": 3.5,
            "flood_extent": 0.6,
            "casualties": 2,
            "response_summary": "boats deployed",
        }
        v = embed_payload(payload)
        assert len(v) == EMBEDDING_DIM

    def test_embed_payload_uses_cache(self):
        payload = {"disaster_type": "flood", "district_name": "Kottayam", "rainfall": 50, "river_level": 2.0, "flood_extent": 0.3, "casualties": 0, "response_summary": "test"}
        a = embed_payload(payload)
        b = embed_payload(payload)
        assert a == b


class TestChromaRetrieval:
    def test_count(self):
        # Ensure seeded
        seed_historical_disasters()
        assert count() >= 5

    def test_add_and_search(self):
        # Add a unique disaster
        payload = {
            "disaster_type": "flood",
            "district_name": "Idukki-Test",
            "rainfall": 200.0,
            "river_level": 5.0,
            "flood_extent": 0.9,
            "casualties": 1,
            "response_summary": "test unique payload for search",
        }
        doc_id = add_disaster(payload)
        assert doc_id
        # Search for it
        emb = embed_payload(payload)
        results = search_similars(emb, top_k=3)
        assert len(results) >= 1
        # The added doc should be among top results (distance small)
        assert any(r["metadata"].get("district_name") == "Idukki-Test" for r in results)

    def test_search_returns_metadata_and_distance(self):
        emb = embed_payload(SAMPLE_DISASTERS[0])
        res = search_similars(emb, top_k=2)
        assert len(res) <= 2
        for r in res:
            assert "id" in r
            assert "distance" in r
            assert "metadata" in r
            assert isinstance(r["distance"], float)

    def test_seed_idempotent(self):
        before = count()
        added = seed_historical_disasters()
        after = count()
        assert added == 0  # already seeded
        assert before == after


class TestChromaTuning:
    def test_tuned_config(self):
        from backend.optimization.chroma_tuning import get_tuned_hnsw_config, TUNED_HNSW_CONFIG

        cfg = get_tuned_hnsw_config()
        assert cfg["hnsw:space"] == "cosine"
        assert cfg["hnsw:M"] == TUNED_HNSW_CONFIG["hnsw:M"]
        assert cfg["hnsw:construction_ef"] == 200

    def test_batch_search(self):
        from backend.optimization.chroma_tuning import batch_search

        embs = [embed_payload(d) for d in SAMPLE_DISASTERS[:2]]
        res = batch_search(embs, top_k=2)
        assert len(res) == 2
        assert all(isinstance(r, list) for r in res)

    def test_benchmark(self):
        from backend.optimization.chroma_tuning import benchmark_search

        embs = [embed_payload(SAMPLE_DISASTERS[0])]
        stats = benchmark_search(embs, top_k=2, warmup=0)
        assert stats["num_queries"] == 1
        assert "p50_ms" in stats
        assert "qps" in stats
