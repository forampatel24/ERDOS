"""Flink stream processing and feature engineering jobs.

Provides the pure-Python :class:`FeatureEngineer` used to emulate the
documented Apache Flink window aggregation pipeline inside the ERDOS streaming
layer.
"""

from backend.streaming.flink.feature_engineering import (
    DEFAULT_WINDOW_SECONDS,
    FeatureEngineer,
)

__all__ = ["FeatureEngineer", "DEFAULT_WINDOW_SECONDS"]