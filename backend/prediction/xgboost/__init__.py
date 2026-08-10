"""Road flood risk prediction (XGBoost sub-model)."""

from backend.prediction.xgboost.features import (
    FEATURE_COLUMNS,
    build_road_features,
    road_static_features,
)
from backend.prediction.xgboost.model import RoadFloodClassifier
from backend.prediction.xgboost.predict import (
    accessibility_for,
    flood_probability_for,
    predict_road_risks,
)
from backend.prediction.xgboost.train import (
    TRAINED_MODEL_PATH,
    build_training_dataset,
    split_chronological,
    train_xgboost,
)

__all__ = [
    "FEATURE_COLUMNS",
    "build_road_features",
    "road_static_features",
    "RoadFloodClassifier",
    "accessibility_for",
    "predict_road_risks",
    "flood_probability_for",
    "build_training_dataset",
    "split_chronological",
    "train_xgboost",
    "TRAINED_MODEL_PATH",
]