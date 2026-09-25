"""Phase 8: Optimization — Ray, performance tuning, ChromaDB vector search tuning."""

from backend.optimization.performance import timed, BatchProcessor, TTLCache
from backend.optimization.ray_utils import is_ray_available, init_ray, parallel_predict, parallel_route
from backend.optimization.chroma_tuning import get_tuned_hnsw_config, benchmark_search

__all__ = [
    "timed",
    "BatchProcessor",
    "TTLCache",
    "is_ray_available",
    "init_ray",
    "parallel_predict",
    "parallel_route",
    "get_tuned_hnsw_config",
    "benchmark_search",
]
