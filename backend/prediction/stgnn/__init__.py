"""Flood propagation spatio-temporal GNN model."""

from backend.prediction.stgnn.graph import (
    DEFAULT_HORIZON,
    FLOOD_WATER_DEPTH_M,
    build_spatiotemporal_graph,
)
from backend.prediction.stgnn.model import (
    SpatioTemporalGNN,
    build_model,
    require_torch,
    torch_available,
)
from backend.prediction.stgnn.predict import predict_propagation
from backend.prediction.stgnn.train import (
    CHECKPOINT_STGNN_PATH,
    TRAINED_STGNN_PATH,
    train_stgnn,
)

__all__ = [
    "DEFAULT_HORIZON",
    "FLOOD_WATER_DEPTH_M",
    "build_spatiotemporal_graph",
    "SpatioTemporalGNN",
    "build_model",
    "require_torch",
    "torch_available",
    "predict_propagation",
    "train_stgnn",
    "CHECKPOINT_STGNN_PATH",
    "TRAINED_STGNN_PATH",
]