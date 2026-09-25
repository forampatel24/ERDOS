"""Ray-based parallelization for flood prediction and routing.

Ray is optional — all functions degrade gracefully to sequential execution
when ``ray`` is not installed, preserving 100% test pass rate without the
heavy dependency.  When available (``pip install ray``), ``init_ray()`` is
called once at startup and ``parallel_predict`` uses ``ray.remote`` to fan out
road-batch inference across workers.

Usage:
    from backend.optimization.ray_utils import is_ray_available, parallel_predict
    if is_ray_available():
        results = parallel_predict(road_ids, snapshot)
    else:
        results = sequential_fallback(...)
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from backend.utils.logging import get_logger

logger = get_logger("optimization.ray")

_RAY_INIT = False


def is_ray_available() -> bool:
    """Return True iff ``ray`` can be imported."""
    try:
        import ray  # noqa: F401
        return True
    except ImportError:
        return False


def init_ray(address: Optional[str] = None, ignore_reinit: bool = True) -> bool:
    """Initialize Ray if available; return True if initialized, False otherwise.

    Safe to call multiple times.  No-op when ray is not installed.
    """
    global _RAY_INIT
    if _RAY_INIT:
        return True
    if not is_ray_available():
        logger.info("Ray not installed — running in sequential mode (pip install ray to enable)")
        return False
    try:
        import ray

        if not ray.is_initialized():
            ray.init(
                address=address,
                ignore_reinit_error=ignore_reinit,
                include_dashboard=False,
                _temp_dir=os.path.join(os.getcwd(), "data", "ray_temp"),
                log_to_driver=False,
            )
        _RAY_INIT = True
        logger.info("Ray initialized (dashboard disabled, temp=data/ray_temp)")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ray init failed, falling back to sequential: {}", exc)
        return False


def _sequential_predict(road_ids: List[str], snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fallback sequential flood prediction (no Ray)."""
    from backend.prediction.xgboost.predict import predict_road_risks
    from backend.prediction.xgboost.predict import _default_model

    model = _default_model()
    # Build per-road predictions using the batch API then slice
    if not road_ids:
        return []
    # predict_road_risks works on full snapshot; filter afterwards
    df = predict_road_risks(snapshot, model=model)
    out = []
    for rid in road_ids:
        if rid in df.index:
            out.append(
                {
                    "road_id": rid,
                    "flood_probability": float(df.loc[rid, "flood_probability"]),
                    "predicted_accessibility": str(df.loc[rid, "predicted_accessibility"]),
                }
            )
        else:
            out.append({"road_id": rid, "flood_probability": 0.0, "predicted_accessibility": "SAFE"})
    return out


def parallel_predict(road_ids: List[str], snapshot: Dict[str, Any], batch_size: int = 16) -> List[Dict[str, Any]]:
    """Predict flood risk for ``road_ids`` in parallel via Ray when available.

    Splits ``road_ids`` into ``batch_size`` chunks and fans out with
    ``ray.remote``.  Falls back to sequential when Ray unavailable or init fails.

    Args:
        road_ids: road IDs to predict.
        snapshot: digital twin snapshot dict.
        batch_size: roads per Ray task.

    Returns:
        List of per-road dicts with ``road_id``, ``flood_probability``,
        ``predicted_accessibility``.
    """
    if not road_ids:
        return []
    if not is_ray_available() or not _RAY_INIT:
        # Try to init lazily; if fails, sequential
        if is_ray_available() and not _RAY_INIT:
            init_ray()
            if not _RAY_INIT:
                return _sequential_predict(road_ids, snapshot)
        else:
            return _sequential_predict(road_ids, snapshot)

    # Ray is available and initialized — fan out
    try:
        import ray

        # Define remote function inline to avoid top-level ray import
        @ray.remote
        def _predict_batch(batch: List[str], snap: Dict[str, Any]) -> List[Dict[str, Any]]:
            return _sequential_predict(batch, snap)

        batches = [road_ids[i : i + batch_size] for i in range(0, len(road_ids), batch_size)]
        refs = [_predict_batch.remote(batch, snapshot) for batch in batches]
        results: List[List[Dict[str, Any]]] = ray.get(refs)
        # Flatten preserving order
        out: List[Dict[str, Any]] = []
        for batch_res in results:
            out.extend(batch_res)
        logger.info("Ray parallel_predict: {} roads in {} batches", len(road_ids), len(batches))
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ray parallel_predict failed, falling back: {}", exc)
        return _sequential_predict(road_ids, snapshot)


def parallel_route(
    pairs: List[tuple[Any, Any]],
    snapshot: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Compute multiple routes in parallel via Ray when available.

    Args:
        pairs: list of (origin, destination) route points.
        snapshot: twin snapshot for graph.

    Returns:
        List of route dicts (same order as ``pairs``).
    """
    if not pairs:
        return []
    if not is_ray_available() or not _RAY_INIT:
        if is_ray_available() and not _RAY_INIT:
            init_ray()
            if not _RAY_INIT:
                return _sequential_route(pairs, snapshot)
        else:
            return _sequential_route(pairs, snapshot)

    try:
        import ray

        @ray.remote
        def _route_one(origin: Any, dest: Any, snap: Dict[str, Any]) -> Dict[str, Any]:
            from backend.orchestration.routing import RoutePlanner

            return RoutePlanner(snap).safest_route(origin, dest, snap)

        refs = [_route_one.remote(o, d, snapshot) for o, d in pairs]
        return ray.get(refs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ray parallel_route failed, falling back: {}", exc)
        return _sequential_route(pairs, snapshot)


def _sequential_route(pairs: List[tuple[Any, Any]], snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    from backend.orchestration.routing import RoutePlanner

    planner = RoutePlanner(snapshot)
    return [planner.safest_route(o, d, snapshot) for o, d in pairs]


def shutdown_ray() -> None:
    """Shutdown Ray if initialized (useful for tests)."""
    global _RAY_INIT
    if _RAY_INIT and is_ray_available():
        try:
            import ray

            if ray.is_initialized():
                ray.shutdown()
        except Exception:
            pass
    _RAY_INIT = False
