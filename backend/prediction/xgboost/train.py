"""Bootstrap training for the XGBoost road flood classifier.

The trainer combines the *real* downloaded Kerala daily weather dataset
(``datasets/processed/kerala_daily_weather.csv``) with the static road
attributes of the digital twin to build a tabular road-day corpus, labels every
road-day with the documented bootstrap rule

    flooded  <=>  precipitation_sum >= FLOOD_RAIN_THRESHOLD_MM

and trains a small/medium XGBoost model with a strictly chronological
70/15/15 train/validation/test split (no random temporal shuffling, per
``docs/ML_PIPELINE.md`` §13).

Sampling keeps the corpus small and class-balanced enough for a laptop:
every day with ``precipitation_sum >= RAINY_FLOOR_MM`` is kept (this captures
all label-positive days), while the remaining dry days are sub-sampled every
``BACKGROUND_STRIDE`` days per place. Rows are emitted in global date order so
the chronological split reduces to row slicing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from backend.digital_twin.builder import DigitalTwinBuilder
from backend.digital_twin.state_manager import StateManager
from backend.prediction.xgboost.features import (
    FEATURE_COLUMNS,
    distance_to_nearest_shelter_km,
    road_static_features,
)
from backend.prediction.xgboost.model import RoadFloodClassifier
from backend.utils.logging import get_logger
from config.constants import MODELLING_ROOT, XGBOOST_MODEL_PATH

logger = get_logger("prediction.xgboost.train")

#: Bootstrap label rule threshold (mm/day).
FLOOD_RAIN_THRESHOLD_MM = 75.0
#: Keep every day at or above this rainfall so positive days are never dropped.
RAINY_FLOOR_MM = 40.0
#: Sub-sample the remaining (dry) days every N days per place.
BACKGROUND_STRIDE = 14

#: Default weather source path (relative to the repository root).
DEFAULT_WEATHER_CSV = str(Path("datasets") / "processed" / "kerala_daily_weather.csv")

#: Chronological split fractions (train, validation, test).
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15

#: Trained model export paths.
TRAINED_MODEL_PATH = f"{MODELLING_ROOT}/trained/xgboost_model.pkl"
METADATA_PATH = f"{MODELLING_ROOT}/metadata/xgboost_metadata.json"


def _load_weather(weather_csv: str) -> pd.DataFrame:
    """Load and normalize the daily weather dataset (date, place, proxies)."""
    path = Path(weather_csv)
    if not path.exists():
        raise FileNotFoundError(
            f"Weather dataset not found at {path}. Download/preprocess it first."
        )
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame.sort_values(["place", "date"]).reset_index(drop=True)
    frame["place"] = frame["place"].astype(str).str.strip()
    frame["precipitation_sum"] = pd.to_numeric(frame["precipitation_sum"], errors="coerce").fillna(0.0)
    return frame


def _add_water_proxies(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive a physical water-level proxy and its rise rate per place.

    ``water_level`` lags rainfall: the 3-day accumulated rain from the previous
    days plus a fraction of today's rain (documented bootstrap proxy, clamped to
    a plausible 0-8 m gauge range). ``water_rise_rate`` is the day-over-day
    positive change. Values are computed on the full per-place series and are
    shared by every road on that place/day.
    """
    out = frame.copy()
    out["water_level"] = np.nan
    out["water_rise_rate"] = np.nan
    for _, group in out.groupby("place", sort=False):
        # The frame was sorted by (place, date) so group order is chronological.
        rain = group["precipitation_sum"].to_numpy(dtype=float)
        previous_3d = pd.Series(rain).rolling(window=3, min_periods=1).sum().shift(1).fillna(0.0).to_numpy()
        water_level = np.clip(previous_3d * 0.02 + rain * 0.015, 0.0, 8.0)
        rise = np.concatenate([[0.0], np.maximum(0.0, water_level[1:] - water_level[:-1])])
        out.loc[group.index, "water_level"] = water_level
        out.loc[group.index, "water_rise_rate"] = rise
    return out


def _sample_days(frame: pd.DataFrame) -> pd.DataFrame:
    """Select the training dates: all rainy days + a sub-sample of dry days."""
    heavy = frame[frame["precipitation_sum"] >= RAINY_FLOOR_MM].copy()
    background = frame[frame["precipitation_sum"] < RAINY_FLOOR_MM].copy()
    background["_rank"] = background.groupby("place").cumcount() + 1
    background = background[background["_rank"] % BACKGROUND_STRIDE == 1].drop(columns="_rank")
    sampled = pd.concat([heavy, background], ignore_index=True)
    sampled = sampled.drop_duplicates(subset=["date", "place"])
    return sampled.sort_values("date").reset_index(drop=True)


def _default_snapshot() -> dict[str, Any]:
    """Build a digital twin snapshot with the built-in Kochi infrastructure.

    Uses an independent :class:`StateManager` so training never mutates the
    process-wide singleton used by the live system.
    """
    state_manager = StateManager()
    DigitalTwinBuilder(state_manager=state_manager).register_default_infrastructure()
    return state_manager.get_snapshot()


def build_training_dataset(
    weather_csv: str = DEFAULT_WEATHER_CSV,
    snapshot: Optional[dict[str, Any]] = None,
) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Assemble the bootstrap road-day training corpus.

    :param weather_csv: path to the processed daily weather CSV.
    :param snapshot: optional digital twin snapshot providing road static
        features; defaults to the built-in Kochi infrastructure.
    :returns: ``(X, y, feature_names)`` where ``X`` has the canonical
        :data:`FEATURE_COLUMNS`, ``y`` holds binary flood labels and rows are
        emitted in strict chronological (date) order.
    """
    weather = _add_water_proxies(_load_weather(weather_csv))
    sampled = _sample_days(weather)
    if snapshot is None:
        snapshot = _default_snapshot()

    roads = snapshot.get("roads") or {}
    if not roads:
        raise ValueError("Snapshot contains no roads; cannot build road-day rows.")
    statics = {
        rid: {**road_static_features(road), "distance_to_shelter_km": distance_to_nearest_shelter_km(snapshot, road)}
        for rid, road in roads.items()
    }

    rows: list[dict[str, float]] = []
    labels: list[int] = []
    for record in sampled.itertuples(index=False):
        precipitation = float(record.precipitation_sum)
        label = 1 if precipitation >= FLOOD_RAIN_THRESHOLD_MM else 0
        water_level = float(getattr(record, "water_level", 0.0))
        water_rise_rate = float(getattr(record, "water_rise_rate", 0.0))
        for static in statics.values():
            features: dict[str, float] = {**static}
            features["rainfall_mm"] = precipitation
            features["water_level"] = water_level
            features["water_rise_rate"] = water_rise_rate
            features["traffic_density"] = 0.5
            features["neighbour_flooded"] = 0.0
            rows.append({column: features[column] for column in FEATURE_COLUMNS})
            labels.append(label)

    X = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
    X.index.name = "road_id"
    y = np.asarray(labels, dtype=np.int64)
    logger.info(
        "Built training dataset: {} rows, {} positive ({}%)",
        len(X),
        int(y.sum()),
        round(100.0 * float(y.mean()), 2),
    )
    return X, y, list(FEATURE_COLUMNS)


def split_chronological(
    X: pd.DataFrame,
    y: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Split chronologically by row order into train/validation/test.

    We rely on :func:`build_training_dataset` emitting rows in increasing date
    order (documented invariant), so slicing the frame is equivalent to a
    temporal split without shuffling. Fractions follow ML_PIPELINE.md §13
    (70/15/15).
    """
    total = len(X)
    train_end = int(round(total * TRAIN_FRAC))
    val_end = int(round(total * (TRAIN_FRAC + VAL_FRAC)))
    return (
        X.iloc[:train_end],
        X.iloc[train_end:val_end],
        X.iloc[val_end:],
        y[:train_end],
        y[train_end:val_end],
        y[val_end:],
    )


def _binary_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray
) -> dict[str, float | None]:
    """Compute accuracy/precision/recall/f1 and ROC-AUC (None if degenerate)."""
    auc: float | None
    if len(np.unique(y_true)) > 1:
        auc = float(roc_auc_score(y_true, y_proba))
    else:
        auc = None
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc": auc,
    }


def train_xgboost(
    weather_csv: str = DEFAULT_WEATHER_CSV,
    snapshot: Optional[dict[str, Any]] = None,
    save_model: bool = True,
) -> dict[str, Any]:
    """Train and export the XGBoost road flood classifier.

    :param weather_csv: weather dataset path used for the bootstrap corpus.
    :param snapshot: optional digital twin snapshot with road statics.
    :param save_model: whether to persist the model and metadata after training.
    :returns: a metrics dict with ``train``/``validation``/``test`` sub-dicts.
    """
    X, y, feature_names = build_training_dataset(weather_csv=weather_csv, snapshot=snapshot)
    X_train, X_val, X_test, y_train, y_val, y_test = split_chronological(X, y)

    classifier = RoadFloodClassifier().train(X_train, y_train)
    val_proba = classifier.predict_proba(X_val)
    test_proba = classifier.predict_proba(X_test)

    metrics: dict[str, Any] = {
        "train": _binary_metrics(y_train, classifier.predict(X_train), classifier.predict_proba(X_train)),
        "validation": _binary_metrics(y_val, (val_proba >= classifier.threshold).astype(int), val_proba),
        "test": _binary_metrics(y_test, (test_proba >= classifier.threshold).astype(int), test_proba),
    }

    print("\n=== XGBoost road flood classifier - chronological 70/15/15 split ===")
    print(f"rows: train={len(X_train)} val={len(X_val)} test={len(X_test)}")
    for split_name, split_metrics in metrics.items():
        print(
            f"{split_name:>10}: accuracy={split_metrics['accuracy']:.3f} "
            f"precision={split_metrics['precision']:.3f} recall={split_metrics['recall']:.3f} "
            f"f1={split_metrics['f1']:.3f} auc={split_metrics['auc']}"
        )
    print("=" * 68)

    if save_model:
        classifier.save(XGBOOST_MODEL_PATH).save(TRAINED_MODEL_PATH)
        _write_metadata(
            metadata_path=METADATA_PATH,
            classifier=classifier,
            metrics=metrics,
            data_source=str(Path(weather_csv).resolve()),
            num_rows=len(X),
            positive_rows=int(y.sum()),
            split_sizes={"train": len(X_train), "validation": len(X_val), "test": len(X_test)},
        )
    logger.info("XGBoost training finished; test auc={}", metrics["test"].get("auc"))
    return metrics


def _write_metadata(
    metadata_path: str,
    classifier: RoadFloodClassifier,
    metrics: dict[str, Any],
    data_source: str,
    num_rows: int,
    positive_rows: int,
    split_sizes: dict[str, int],
) -> None:
    """Persist the training metadata JSON next to the trained model."""
    metadata = {
        "model": "XGBClassifier (xgboost, sklearn API)",
        "version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": classifier.feature_names(),
        "class_names": ["NOT_FLOODED", "FLOODED"],
        "threshold": classifier.threshold,
        "label_rule": (
            f"flooded if precipitation_sum >= {FLOOD_RAIN_THRESHOLD_MM} mm on the "
            "road's place/date (documented bootstrap fallback until real flood maps arrive)"
        ),
        "label_rule_threshold_mm": FLOOD_RAIN_THRESHOLD_MM,
        "data_source": data_source,
        "num_rows": num_rows,
        "positive_rows": positive_rows,
        "split_fractions": {"train": TRAIN_FRAC, "validation": VAL_FRAC, "test": 1.0 - TRAIN_FRAC - VAL_FRAC},
        "split_sizes": split_sizes,
        "metrics": {name: {"auc": m["auc"], **{k: round(v, 4) for k, v in m.items() if k != "auc"}} for name, m in metrics.items()},
        "auc": metrics["test"]["auc"],
    }
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
    logger.info("Wrote XGBoost metadata to {}", path)


__all__ = [
    "FLOOD_RAIN_THRESHOLD_MM",
    "build_training_dataset",
    "split_chronological",
    "train_xgboost",
    "TRAINED_MODEL_PATH",
    "METADATA_PATH",
]