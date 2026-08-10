"""Evaluate the trained XGBoost road flood model on the test split.

Loads the exported :class:`RoadFloodClassifier`, rebuilds the bootstrap
road-day corpus with the same chronological 70/15/15 split used at training and
prints a full classification report, ROC-AUC and accuracy for the held-out test
set. Nothing is written to disk.

Run from the repository root so ``backend``/``config`` are importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    roc_auc_score,
)

from backend.prediction.xgboost.model import RoadFloodClassifier  # noqa: E402
from backend.prediction.xgboost.train import (  # noqa: E402
    TRAINED_MODEL_PATH,
    build_training_dataset,
    split_chronological,
)
from backend.utils.logging import get_logger  # noqa: E402
from config.constants import XGBOOST_MODEL_PATH  # noqa: E402

logger = get_logger("scripts.evaluate_models")


def _load_model() -> RoadFloodClassifier:
    """Load the trained classifier from the standard export locations."""
    for candidate in (TRAINED_MODEL_PATH, XGBOOST_MODEL_PATH):
        model = RoadFloodClassifier.load(candidate)
        if model is not None:
            return model
    raise SystemExit(
        f"No trained XGBoost model found at {TRAINED_MODEL_PATH} / {XGBOOST_MODEL_PATH}. "
        "Run `python scripts/train_models.py --xgboost` first."
    )


def main(argv: list[str] | None = None) -> int:
    """Evaluate the trained model on the chronological test split."""
    model = _load_model()

    X, y, _ = build_training_dataset()
    _, _, X_test, _, _, y_test = split_chronological(X, y)

    y_proba = model.predict_proba(X_test)
    y_pred = model.predict(X_test)

    print("\n=== XGBoost road flood model - held-out test evaluation ===")
    print(f"test rows: {len(X_test)}  positives: {int(y_test.sum())}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=["NOT_FLOODED", "FLOODED"], zero_division=0))
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.4f}")
    if len(set(y_test.tolist())) > 1:
        print(f"ROC-AUC  : {roc_auc_score(y_test, y_proba):.4f}")
    else:
        print("ROC-AUC  : undefined (test split contains a single class)")
    print("=" * 60)
    logger.info("Evaluation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())