"""Spatio-temporal GNN for flood propagation prediction (PyTorch Geometric).

:class:`SpatioTemporalGNN` runs a temporal GRU over the per-node feature window
and then applies message-passing ``GraphConv`` layers on the road/infrastructure
graph at every timestep to output a per-node flood probability per timestep.

``torch`` and ``torch_geometric`` are imported lazily at construction /
forward time. Importing this module never requires them; constructing a
:class:`SpatioTemporalGNN` instance swaps in the real PyTorch module (a
``torch.nn.Module``) via the lazy subclass creator in :func:`_model_class`, so
``isinstance(model, torch.nn.Module)`` and ``isinstance(model,
SpatioTemporalGNN)`` both hold once constructed.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.utils.logging import get_logger

logger = get_logger("prediction.stgnn.model")

#: Cached real PyTorch class created on first construction.
_MODEL_CLASS: Optional[type] = None


def require_torch() -> tuple[Any, Any]:
    """Import ``torch`` lazily or raise an informative :class:`RuntimeError`.

    :returns: ``(torch, torch.nn module)``.
    """
    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "torch is required to construct/train the ST-GNN model. "
            "Install it with `pip install torch torch-geometric` and retry."
        ) from exc
    return torch, nn


def _model_class() -> type:
    """Create (once) and cache the real PyTorch ST-GNN class.

    The class subclasses both ``torch.nn.Module`` and :class:`SpatioTemporalGNN`
    so every constructed instance exposes the documented interface and a torch
    module identity. Requires torch and torch-geometric.
    """
    global _MODEL_CLASS
    if _MODEL_CLASS is not None:
        return _MODEL_CLASS

    torch, nn = require_torch()
    try:
        from torch_geometric.nn import GraphConv  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "torch_geometric is required for the ST-GNN message-passing layers. "
            "Install it with `pip install torch-geometric` and retry."
        ) from exc

    class _SpatioTemporalGNNImpl(SpatioTemporalGNN, torch.nn.Module):
        """Temporal GRU + per-step GraphConv message passing (ST-GNN)."""

        def __init__(
            self,
            in_channels: int = 4,
            hidden_channels: int = 32,
            out_channels: int = 1,
            horizon: int = 6,
            num_gcn_layers: int = 2,
            dropout: float = 0.2,
        ) -> None:
            super().__init__()
            self.horizon = int(horizon)
            self.config: dict[str, Any] = {
                "in_channels": in_channels,
                "hidden_channels": hidden_channels,
                "out_channels": out_channels,
                "horizon": self.horizon,
                "num_gcn_layers": num_gcn_layers,
                "dropout": dropout,
            }
            self.temporal: Any = nn.GRU(
                input_size=in_channels,
                hidden_size=hidden_channels,
                num_layers=1,
                batch_first=False,
            )
            self.gcn_layers: Any = torch.nn.ModuleList(
                [GraphConv(hidden_channels, hidden_channels) for _ in range(num_gcn_layers - 1)]
                + [GraphConv(hidden_channels, out_channels)]
            )
            self.activation = nn.ReLU()
            self.dropout = nn.Dropout(p=dropout)

        def forward(self, node_features: Any, edge_index: Any, edge_weight: Any = None) -> Any:
            """Produce per-node flood probabilities for every timestep.

            :param node_features: ``(T, N, C)`` tensor or array-like.
            :param edge_index: ``(2, E)`` integer tensor or array-like.
            :param edge_weight: optional ``(E,)`` edge weights.
            :returns: ``(T, N)`` float tensor of flood probabilities.
            """
            data = _to_tensors(user_features=node_features, user_edges=edge_index, user_weights=edge_weight)
            node_features_t, edge_index_t, edge_weight_t = data

            temporal_out: Any
            temporal_out, _ = self.temporal(node_features_t)  # (T, N, hidden)

            step_logits = []
            for step in range(temporal_out.size(0)):
                hidden = temporal_out[step]
                for layer in self.gcn_layers[:-1]:
                    hidden = layer(hidden, edge_index_t, edge_weight_t)
                    hidden = self.activation(hidden)
                    hidden = self.dropout(hidden)
                step_logits.append(self.gcn_layers[-1](hidden, edge_index_t, edge_weight_t))
            logits = torch.stack(step_logits, dim=0)  # (T, N, 1)
            return torch.sigmoid(logits.squeeze(-1))

        def predict_numpy(self, graph: dict[str, Any]) -> np.ndarray:
            """Run :meth:`forward` on a graph dict, returning numpy probabilities."""
            probabilities = self.forward(
                graph["node_features"],
                graph["edge_index"],
                graph["edge_weight"],
            )
            return probabilities.detach().cpu().numpy()

    _MODEL_CLASS = _SpatioTemporalGNNImpl
    return _MODEL_CLASS


def _to_tensors(user_features: Any, user_edges: Any, user_weights: Any) -> tuple[Any, Any, Any]:
    """Coerce the graph dict entries to torch tensors (helper for forward)."""
    torch, _ = require_torch()
    features = torch.as_tensor(np.asarray(user_features), dtype=torch.float32)
    edges = torch.as_tensor(np.asarray(user_edges), dtype=torch.long)
    weights = (
        None
        if user_weights is None
        else torch.as_tensor(np.asarray(user_weights), dtype=torch.float32)
    )
    return features, edges, weights


class SpatioTemporalGNN:
    """Spatio-temporal GNN facade. Import-safe without torch.

    Constructing an instance lazily builds the underlying PyTorch module; the
    returned object is a real ``torch.nn.Module`` exposing ``forward`` /
    ``predict_numpy`` and a ``config`` dict.
    """

    # Forward-declared attributes set by the real implementation.
    config: dict[str, Any]
    horizon: int

    def __new__(cls, *args: Any, **kwargs: Any) -> "SpatioTemporalGNN":
        return _model_class()(*args, **kwargs)


def torch_available() -> bool:
    """Return True when torch and torch-geometric can be imported."""
    try:
        require_torch()
        _, _ = _model_class()
    except RuntimeError:
        return False
    return True


__all__ = ["SpatioTemporalGNN", "require_torch", "torch_available", "build_model"]


def build_model(**kwargs: Any) -> SpatioTemporalGNN:
    """Create a usable :class:`SpatioTemporalGNN` instance (lazy torch import).

    :raises RuntimeError: when torch or torch-geometric is not installed.
    """
    return SpatioTemporalGNN(**kwargs)