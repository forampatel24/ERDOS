"""XGBoost wrapper for the ERDOS road flood classifier.

:class:`RoadFloodClassifier` wraps the installed ``xgboost`` sklearn API behind
a small, stable interface used by both the training pipeline and the live
inference path. Persistence relies on ``joblib``; ``save``/``load`` store the
whole wrapper (including the learned feature-name contract) so predictions can
always be re-aligned to the exact training columns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from backend.utils.logging import get_logger

logger = get_logger("prediction.xgboost.model")

#: Default probability threshold used to turn model output into hard labels.
DEFAULT_THRESHOLD = 0.5

PathLike = Union[str, Path]


class RoadFloodClassifier:
    """Binary XGBoost classifier predicting the probability a road floods."""

    def __init__(self, model: Optional[xgb.XGBClassifier] = None) -> None:
        """Wrap an optional pre-built :class:`xgb.XGBClassifier`."""
        self.model: Optional[xgb.XGBClassifier] = model
        self._feature_names: list[str] = []
        self._positive_index: int = 1

    # ------------------------------------------------------------------ train

    def train(self, X: Any, y: Any) -> "RoadFloodClassifier":
        """Fit the XGBoost classifier on a feature frame and binary labels.

        :param X: feature DataFrame (columns act as the feature-name contract).
        :param y: 1-D array-like of 0/1 flood labels.
        :returns: ``self`` for chaining.
        """
        frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        target = np.asarray(y, dtype=np.int64)
        self._feature_names = list(frame.columns)
        positives = int(target.sum())
        negatives = int(len(target) - target.sum())
        scale_pos_weight = negatives / positives if positives > 0 else 1.0

        clf = xgb.XGBClassifier(
            objective="binary:logistic",
            tree_method="hist",
            max_depth=5,
            n_estimators=200,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(frame, target)
        self.model = clf
        classes = list(clf.classes_)
        self._positive_index = classes.index(1) if 1 in classes else 0
        logger.info(
            "Trained RoadFloodClassifier on {} rows ({} positives)",
            len(frame),
            positives,
        )
        return self

    # ---------------------------------------------------------------- predict

    def _require_model(self) -> None:
        if self.model is None:
            raise RuntimeError(
                "RoadFloodClassifier has no fitted model; call train(...) or load(path) first."
            )

    def _prepare_matrix(self, X: Any) -> pd.DataFrame:
        frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        if self._feature_names:
            missing = [column for column in self._feature_names if column not in frame.columns]
            if missing:
                raise ValueError(
                    f"Model expects feature columns {self._feature_names[:3]}...; "
                    f"missing from input: {missing}"
                )
            frame = frame[self._feature_names]
        return frame.fillna(0.0)

    def predict_proba(self, X: Any) -> np.ndarray:
        """Return positive-class (flooded) probability per row in ``[0, 1]``."""
        self._require_model()
        assert self.model is not None
        matrix = self._prepare_matrix(X)
        probabilities = np.asarray(self.model.predict_proba(matrix))
        return np.clip(probabilities[:, self._positive_index], 0.0, 1.0)

    def predict(self, X: Any, threshold: float = DEFAULT_THRESHOLD) -> np.ndarray:
        """Return hard 0/1 predictions at the given probability threshold."""
        return (self.predict_proba(X) >= threshold).astype(int)

    def feature_names(self) -> list[str]:
        """Return the exact feature columns the model was trained on."""
        return list(self._feature_names)

    @property
    def threshold(self) -> float:
        """Default probability threshold used for hard predictions."""
        return DEFAULT_THRESHOLD

    # ---------------------------------------------------------------- persist

    def save(self, path: PathLike) -> "RoadFloodClassifier":
        """Serialize the classifier via joblib, creating parent dirs."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target)
        logger.info("Saved RoadFloodClassifier to {}", target)
        return self

    @classmethod
    def load(cls, path: PathLike) -> Optional["RoadFloodClassifier"]:
        """Load a classifier, returning ``None`` (not raising) when absent.

        An informative :class:`ValueError` is raised when the file exists but
        does not contain a :class:`RoadFloodClassifier`.
        """
        target = Path(path)
        if not target.exists():
            return None
        payload: Any = joblib.load(target)
        if not isinstance(payload, cls):
            raise ValueError(
                f"{target} does not contain a RoadFloodClassifier "
                f"(found {type(payload).__name__})."
            )
        logger.info("Loaded RoadFloodClassifier from {}", target)
        return payload


__all__ = ["RoadFloodClassifier", "DEFAULT_THRESHOLD"]