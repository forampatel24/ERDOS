"""Train the ERDOS prediction models (XGBoost + optional ST-GNN).

CLI:

    python scripts/train_models.py --xgboost   # bootstrap-train and export XGBoost
    python scripts/train_models.py --stgnn     # train ST-GNN (gracefully skipped without torch)
    python scripts/train_models.py --all       # both

Run from the repository root so ``backend``/``config`` are importable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.prediction.stgnn.train import train_stgnn  # noqa: E402
from backend.prediction.xgboost.train import (  # noqa: E402
    METADATA_PATH,
    TRAINED_MODEL_PATH,
    train_xgboost,
)
from backend.utils.logging import get_logger  # noqa: E402
from config.constants import XGBOOST_MODEL_PATH  # noqa: E402

logger = get_logger("scripts.train_models")

#: ST-GNN export paths (printed when training succeeds).
STGNN_CHECKPOINT_PATH = "models/checkpoints/stgnn_model.pt"
STGNN_TRAINED_PATH = "models/trained/stgnn_model.pt"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the CLI arguments."""
    parser = argparse.ArgumentParser(description="Train ERDOS prediction models.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--xgboost", action="store_true", help="Train the XGBoost road flood model.")
    group.add_argument("--stgnn", action="store_true", help="Train the ST-GNN propagation model.")
    group.add_argument("--all", action="store_true", help="Train both models.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point: run the requested training step(s) and report artifacts."""
    args = parse_args(argv)

    if args.xgboost or args.all:
        logger.info("Starting XGBoost bootstrap training...")
        metrics = train_xgboost()
        print("\nArtifacts written:")
        print(f"  - XGBoost model: {XGBOOST_MODEL_PATH}")
        print(f"  - Trained copy : {TRAINED_MODEL_PATH}")
        print(f"  - Metadata     : {METADATA_PATH}")
        logger.info("XGBoost training completed: {}", metrics["test"])

    if args.stgnn or args.all:
        logger.info("Starting ST-GNN training...")
        result = train_stgnn()
        if result.get("status") == "trained":
            print(f"  - ST-GNN checkpoint: {STGNN_CHECKPOINT_PATH}")
            print(f"  - ST-GNN trained   : {STGNN_TRAINED_PATH}")
            logger.info("ST-GNN training completed: {}", result.get("validation"))
        else:
            print(f"  - ST-GNN training skipped: {result.get('reason')}")

    logger.info("Model training finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())