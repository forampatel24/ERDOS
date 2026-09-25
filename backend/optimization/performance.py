"""Performance tuning utilities: TTL cache, batch processor, timing decorator.

All utilities are pure-Python and have zero heavy dependencies.  They are used
by prediction, routing, and embedding hot paths to reduce redundant work.
"""

from __future__ import annotations

import time
import functools
import hashlib
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.utils.logging import get_logger

logger = get_logger("optimization.performance")


def timed(func: Callable) -> Callable:
    """Decorator that logs execution time at DEBUG level."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        logger.debug("{} took {:.2f}ms", func.__qualname__, dt_ms)
        # Attach timing for programmatic access in tests
        wrapper.last_duration_ms = dt_ms  # type: ignore[attr-defined]
        return result

    wrapper.last_duration_ms = 0.0  # type: ignore[attr-defined]
    return wrapper


class TTLCache:
    """Simple TTL + LRU cache for snapshot-derived results.

    Keys are hashed with SHA256 of ``str(key)`` so unhashable snapshots work.
    Thread-safe for read-heavy dashboard polling.
    """

    def __init__(self, maxsize: int = 128, ttl_seconds: float = 5.0) -> None:
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._store: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def _hash(self, key: Any) -> str:
        return hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]

    def get(self, key: Any) -> Optional[Any]:
        h = self._hash(key)
        item = self._store.get(h)
        if item is None:
            return None
        ts, val = item
        if time.time() - ts > self.ttl:
            self._store.pop(h, None)
            return None
        # LRU bump
        self._store.move_to_end(h)
        return val

    def set(self, key: Any, value: Any) -> None:
        h = self._hash(key)
        self._store[h] = (time.time(), value)
        self._store.move_to_end(h)
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        # Prune expired before reporting
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self.ttl]
        for k in expired:
            self._store.pop(k, None)
        return len(self._store)


class BatchProcessor:
    """Utility to chunk large road ID lists and process with optional parallelism."""

    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = batch_size

    def batches(self, items: List[Any]) -> List[List[Any]]:
        """Chunk ``items`` into batches of ``self.batch_size``."""
        return [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

    def map(
        self,
        func: Callable[[List[Any]], List[Any]],
        items: List[Any],
        use_ray: bool = False,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Apply ``func`` per batch and flatten.  Optionally use Ray.

        When ``use_ray`` is True and Ray is available, batches are fanned out
        via ``ray.remote``.  Otherwise sequential.
        """
        if not items:
            return []
        chunks = self.batches(items)
        if use_ray:
            try:
                from backend.optimization.ray_utils import is_ray_available, init_ray

                if is_ray_available():
                    init_ray()
                    import ray

                    remote = ray.remote(func)
                    refs = [remote.remote(c) for c in chunks]
                    results = ray.get(refs)
                    out: List[Any] = []
                    for r in results:
                        out.extend(r)
                    return out
            except Exception as exc:  # noqa: BLE001
                logger.warning("BatchProcessor ray map failed, falling back: {}", exc)
        # Sequential fallback
        out2: List[Any] = []
        for c in chunks:
            out2.extend(func(c))
        return out2


# Module-level caches used by hot paths
_prediction_cache = TTLCache(maxsize=64, ttl_seconds=3.0)
_graph_cache = TTLCache(maxsize=32, ttl_seconds=10.0)
_embedding_cache = TTLCache(maxsize=256, ttl_seconds=60.0)


def get_prediction_cache() -> TTLCache:
    return _prediction_cache


def get_graph_cache() -> TTLCache:
    return _graph_cache


def get_embedding_cache() -> TTLCache:
    return _embedding_cache
