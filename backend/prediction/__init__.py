"""AI inference layer (XGBoost + ST-GNN) for the ERDOS prediction pipeline.

The prediction layer is responsible only for flood prediction and flood
propagation inference (see ``docs/PROJECT_SPEC.md`` Module 5). It consumes the
digital twin snapshot and produces :class:`PredictionOutput` objects that the
Orchestration Engine consumes downstream.
"""

from backend.prediction.inference.output import PredictionOutput
from backend.prediction.inference.pipeline import (
    PredictionPipeline,
    get_prediction_pipeline,
)
from backend.prediction.xgboost import (
    accessibility_for,
    build_road_features,
    predict_road_risks,
    train_xgboost,
)
from backend.prediction.stgnn import (
    build_spatiotemporal_graph,
    predict_propagation,
    train_stgnn,
)

__all__ = [
    "PredictionOutput",
    "PredictionPipeline",
    "get_prediction_pipeline",
    "accessibility_for",
    "build_road_features",
    "predict_road_risks",
    "train_xgboost",
    "build_spatiotemporal_graph",
    "predict_propagation",
    "train_stgnn",
]