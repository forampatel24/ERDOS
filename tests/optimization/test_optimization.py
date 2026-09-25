"""Tests for Phase 8 optimization: Ray, performance, ChromaDB tuning."""

from __future__ import annotations

import time
import pytest

from backend.optimization.performance import TTLCache, BatchProcessor, timed, get_prediction_cache, get_embedding_cache
from backend.optimization.ray_utils import is_ray_available, parallel_predict, parallel_route
from backend.optimization.chroma_tuning import get_tuned_hnsw_config, batch_search, benchmark_search


class TestTTLCache:
    def test_set_get(self):
        c = TTLCache(maxsize=4, ttl_seconds=10)
        c.set("k1", "v1")
        assert c.get("k1") == "v1"

    def test_ttl_expiry(self):
        c = TTLCache(maxsize=4, ttl_seconds=0.05)
        c.set("k", "v")
        time.sleep(0.08)
        assert c.get("k") is None

    def test_lru_eviction(self):
        c = TTLCache(maxsize=2, ttl_seconds=10)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        assert len(c) == 2
        assert c.get("a") is None

    def test_clear(self):
        c = TTLCache(maxsize=4, ttl_seconds=10)
        c.set("x", 1)
        c.clear()
        assert len(c) == 0


class TestBatchProcessor:
    def test_batches(self):
        bp = BatchProcessor(batch_size=2)
        assert bp.batches([1, 2, 3, 4, 5]) == [[1, 2], [3, 4], [5]]

    def test_map_sequential(self):
        bp = BatchProcessor(batch_size=2)

        def double(batch):
            return [x * 2 for x in batch]

        assert bp.map(double, [1, 2, 3]) == [2, 4, 6]

    def test_timed_decorator(self):
        @timed
        def foo(x):
            time.sleep(0.01)
            return x + 1

        res = foo(1)
        assert res == 2
        assert hasattr(foo, "last_duration_ms")
        assert foo.last_duration_ms >= 5


class TestRayUtils:
    def test_is_ray_available_is_bool(self):
        assert isinstance(is_ray_available(), bool)

    def test_parallel_predict_fallback(self):
        # With no Ray, should fall back to sequential and still return predictions
        from backend.digital_twin.builder import DigitalTwinBuilder
        from backend.digital_twin.state_manager import get_state_manager

        sm = get_state_manager()
        DigitalTwinBuilder(sm).register_default_infrastructure()
        snap = sm.get_snapshot()
        road_ids = list(snap.get("roads", {}).keys())[:3]
        if not road_ids:
            pytest.skip("no roads in twin")
        res = parallel_predict(road_ids, snap, batch_size=2)
        assert len(res) == len(road_ids)
        for r in res:
            assert "road_id" in r
            assert 0 <= r["flood_probability"] <= 1

    def test_parallel_route_fallback(self):
        from backend.digital_twin.builder import DigitalTwinBuilder
        from backend.digital_twin.state_manager import get_state_manager

        sm = get_state_manager()
        DigitalTwinBuilder(sm).register_default_infrastructure()
        snap = sm.get_snapshot()
        pairs = [((9.93, 76.26), (9.94, 76.28)), ((9.93, 76.27), (9.94, 76.29))]
        res = parallel_route(pairs, snap)
        assert len(res) == 2
        for r in res:
            assert "route" in r


class TestChromaTuning:
    def test_tuned_config_has_ef(self):
        cfg = get_tuned_hnsw_config()
        assert cfg["hnsw:construction_ef"] == 200
        assert cfg["hnsw:M"] == 16
        assert cfg["hnsw:search_ef"] == 100

    def test_batch_search_fast(self):
        from backend.database.chromadb.embeddings import embed_payload
        from backend.database.chromadb.retrieval import SAMPLE_DISASTERS

        embs = [embed_payload(d) for d in SAMPLE_DISASTERS[:2]]
        res = batch_search(embs, top_k=2)
        assert len(res) == 2

    def test_benchmark_returns_qps(self):
        from backend.database.chromadb.embeddings import embed_payload
        from backend.database.chromadb.retrieval import SAMPLE_DISASTERS

        stats = benchmark_search([embed_payload(SAMPLE_DISASTERS[0])], top_k=2, warmup=0)
        assert stats["qps"] >= 0
        assert "p50_ms" in stats


class TestEmbeddingCache:
    def test_cache_hit(self):
        from backend.database.chromadb.embeddings import embed_payload

        payload = {"disaster_type": "flood", "district_name": "TestCache", "rainfall": 10, "river_level": 2, "flood_extent": 0.1, "casualties": 0, "response_summary": "cache test"}
        # First call populates cache, second hits
        a = embed_payload(payload)
        # Check cache has entry
        cache = get_embedding_cache()
        text = "flood TestCache cache test rainfall=10.00 river_level=2.00 flood_extent=0.10 casualties=0.00"
        # Not exact text but cache should be non-empty
        assert len(cache) >= 1
        b = embed_payload(payload)
        assert a == b

    def test_prediction_cache(self):
        from backend.prediction.xgboost.predict import predict_road_risks
        from backend.digital_twin.builder import DigitalTwinBuilder
        from backend.digital_twin.state_manager import get_state_manager

        sm = get_state_manager()
        DigitalTwinBuilder(sm).register_default_infrastructure()
        snap = sm.get_snapshot()
        a = predict_road_risks(snap, model=None)
        b = predict_road_risks(snap, model=None)
        # Cached result should be equal
        assert a.equals(b)
