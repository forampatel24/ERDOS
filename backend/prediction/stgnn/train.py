"""ST-GNN training pipeline for flood propagation prediction.

:func:`train_stgnn` builds a sequence of digital twin snapshots by running the
disaster simulator, converts them into spatio-temporal graphs, and trains the
:class:`SpatioTemporalGNN` on a supervised per-node, per-timestep flood-status
task (Adam + binary cross-entropy).

The caller-facing entry point is fully graceful: when ``torch`` /
``torch_geometric`` are not installed it prints a clear warning and returns
a ``{"status": "skipped", ...}`` dict instead of raising, so ``scripts/
train_models.py`` can run end-to-end without them. Importing this module never
fails.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.digital_twin.builder import DigitalTwinBuilder
from backend.digital_twin.state_manager import get_state_manager
from backend.prediction.stgnn.graph import build_spatiotemporal_graph
from backend.prediction.stgnn.model import SpatioTemporalGNN, require_torch
from backend.simulator.engine import SimulationEngine
from backend.utils.logging import get_logger
from config.constants import MODELLING_ROOT, STGNN_MODEL_PATH

logger = get_logger("prediction.stgnn.train")

CHECKPOINT_STGNN_PATH = f"{MODELLING_ROOT}/checkpoints/stgnn_model.pt"
TRAINED_STGNN_PATH = f"{MODELLING_ROOT}/trained/stgnn_model.pt"

#: Training configuration defaults.
DEFAULT_HORIZON = 6
DEFAULT_SIM_STEPS = 24
DEFAULT_EPOCHS = 60
DEFAULT_LEARNING_RATE = 1e-3

#: Loss/accuracy reported on the last fraction of samples held out.
VAL_FRACTION = 0.2

#: Statuses considered flooded when building supervised targets.
FLOODED_ROAD_STATUSES: frozenset[str] = frozenset({"BLOCKED", "HIGH_RISK"})
FLOODED_INFRA_STATUSES: frozenset[str] = frozenset({"FLOODED", "DAMAGED", "CLOSED"})


def _torch_ready() -> bool:
    """Return True when torch and torch-geometric are importable."""
    try:
        require_torch()
        from torch_geometric import nn as _  # noqa: F401
    except (RuntimeError, ImportError):  # pragma: no cover - environment dependent
        return False
    return True


def _flood_target_vector(snapshot: dict[str, Any], node_ids: list[str]) -> np.ndarray:
    """Encode the observed flooded state of every graph node in a snapshot."""
    roads = snapshot.get("roads") or {}
    pools = {
        "shelter": snapshot.get("shelters") or {},
        "hospital": snapshot.get("hospitals") or {},
        "bridge": snapshot.get("bridges") or {},
    }
    vector: list[float] = []
    for node_id in node_ids:
        if ":" in node_id:
            kind, entity_id = node_id.split(":", 1)
            entity = pools.get(kind, {}).get(entity_id, {})
            flooded = str(entity.get("status", "")) in FLOODED_INFRA_STATUSES
        else:
            road = roads.get(node_id, {}) if isinstance(roads, dict) else {}
            status = str(road.get("status", ""))
            flood_probability = 0.0
            try:
                flood_probability = float(road.get("flood_probability", 0.0) or 0.0)
            except (TypeError, ValueError):
                flood_probability = 0.0
            flooded = status in FLOODED_ROAD_STATUSES or flood_probability > 0.5
        vector.append(1.0 if flooded else 0.0)
    return np.asarray(vector, dtype=np.float32)


def _build_snapshot_timeline(snapshot: Optional[dict[str, Any]], steps: int) -> list[dict[str, Any]]:
    """Produce a chronological list of twin snapshots via the simulator.

    The initial snapshot (when given) is followed by snapshots captured after
    each simulated advance step, which are pushed into the live state manager.
    """
    timeline: list[dict[str, Any]] = []
    if snapshot is not None:
        timeline.append(snapshot)

    state_manager = get_state_manager()
    if not state_manager.roads:
        DigitalTwinBuilder(state_manager=state_manager).register_default_infrastructure()
    engine = SimulationEngine(state_manager=state_manager)
    for _ in range(steps):
        engine.run(1)
        timeline.append(state_manager.get_snapshot())
    return timeline


def _build_training_samples(
    timeline: list[dict[str, Any]], horizon: int
) -> list[tuple[dict[str, Any], np.ndarray]]:
    """Create ``(graph, target)`` pairs: predict flood statuses ``horizon`` steps ahead."""
    samples: list[tuple[dict[str, Any], np.ndarray]] = []
    for start in range(len(timeline) - horizon):
        graph = build_spatiotemporal_graph(timeline[start], horizon=horizon)
        targets = np.stack(
            [
                _flood_target_vector(timeline[start + step + 1], graph["node_ids"])
                for step in range(horizon)
            ],
            axis=0,
        )  # (horizon, num_nodes)
        samples.append((graph, targets))
    return samples


def train_stgnn(
    snapshot: Optional[dict[str, Any]] = None,
    steps: int = DEFAULT_SIM_STEPS,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    horizon: int = DEFAULT_HORIZON,
) -> dict[str, Any]:
    """Train (or gracefully skip) the ST-GNN flood propagation model.

    :param snapshot: optional initial digital twin snapshot for the timeline.
    :param steps: number of simulator steps to build the supervision timeline.
    :param epochs: number of training epochs.
    :param learning_rate: Adam learning rate.
    :param horizon: forecast horizon (timesteps per graph).
    :returns: an info dict: ``{"status": "trained", ...}`` on success or
        ``{"status": "skipped", "reason": ...}`` when torch is unavailable.
    """
    if not _torch_ready():
        message = (
            "torch / torch-geometric are not installed - skipping ST-GNN training. "
            "Install them with `pip install torch torch-geometric` and rerun."
        )
        logger.warning(message)
        print(f"[SKIP] {message}")
        return {"status": "skipped", "reason": "torch / torch-geometric not installed"}

    torch, nn = require_torch()

    timeline = _build_snapshot_timeline(snapshot, steps)
    samples = _build_training_samples(timeline, horizon)
    if not samples:
        raise ValueError(
            f"Not enough snapshots ({len(timeline)}) to build horizon-{horizon} samples."
        )

    split_at = max(1, int(len(samples) * (1.0 - VAL_FRACTION)))
    train_samples = samples[:split_at]
    val_samples = samples[split_at:]
    logger.info("ST-GNN samples: {} train / {} validation", len(train_samples), len(val_samples))

    model = SpatioTemporalGNN(**model_config(horizon=horizon))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.BCELoss()

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        for graph, target in train_samples:
            optimizer.zero_grad()
            predictions = model(graph["node_features"], graph["edge_index"], graph["edge_weight"])
            target_t = torch.as_tensor(target, dtype=torch.float32)
            loss = loss_fn(predictions, target_t)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item())
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            logger.info("ST-GNN epoch {}/{} avg loss {:.4f}", epoch, epochs, epoch_loss / len(train_samples))

    validation = _validate(model, val_samples, loss_fn)
    print(
        "ST-GNN trained: {} samples, {} epochs, val BCE {:.4f}, val accuracy {:.3f}".format(
            len(samples), epochs, validation["loss"], validation["accuracy"]
        )
    )

    torch.save(
        {"config": model.config, "state_dict": model.state_dict(), "epochs": epochs},
        CHECKPOINT_STGNN_PATH,
    )
    torch.save(
        {"config": model.config, "state_dict": model.state_dict(), "epochs": epochs},
        TRAINED_STGNN_PATH,
    )
    logger.info("Saved ST-GNN model to {} and {}", CHECKPOINT_STGNN_PATH, TRAINED_STGNN_PATH)

    return {
        "status": "trained",
        "epochs": epochs,
        "samples": len(samples),
        "horizon": horizon,
        "validation": validation,
        "checkpoint_path": CHECKPOINT_STGNN_PATH,
        "model_path": TRAINED_STGNN_PATH,
    }


def model_config(horizon: int = DEFAULT_HORIZON) -> dict[str, Any]:
    """Return the ST-GNN architecture configuration used for training."""
    return {
        "in_channels": 4,
        "hidden_channels": 32,
        "out_channels": 1,
        "horizon": horizon,
        "num_gcn_layers": 2,
        "dropout": 0.2,
    }


def _validate(model: SpatioTemporalGNN, samples: list[tuple[dict[str, Any], np.ndarray]], loss_fn: Any) -> dict[str, float]:
    """Evaluate mean BCE and binary accuracy on held-out samples."""
    torch, _ = require_torch()
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for graph, target in samples:
            predictions = model(graph["node_features"], graph["edge_index"], graph["edge_weight"])
            target_t = torch.as_tensor(target, dtype=torch.float32)
            total_loss += float(loss_fn(predictions, target_t).item())
            hard = (predictions >= 0.5).to(torch.int32)
            correct += int((hard == target_t.to(torch.int32)).sum().item())
            total += int(target_t.numel())
    return {"loss": total_loss / len(samples), "accuracy": correct / total}


__all__ = [
    "CHECKPOINT_STGNN_PATH",
    "TRAINED_STGNN_PATH",
    "train_stgnn",
    "model_config",
]