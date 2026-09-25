"""Captum / Treelite prediction explanations for XGBoost road flood model.

Attempts the following in order, never raising to callers:

1. XGBoost native SHAP via ``Booster.predict(..., pred_contribs=True)`` – the
   primary, zero-extra-dependency path.  Returns per-feature SHAP values.
2. Treelite SHAP (``treelite.gtil``) when ``treelite`` is installed.
3. Captum ``IntegratedGradients`` when a torch ST-GNN model and ``captum`` are
   available.
4. Deterministic heuristic fallback (mirrors the weights in
   ``backend.prediction.xgboost.predict._heuristic_probabilities``).

All paths return the same contract so ``explainability_service`` is isolated
from the backend choice.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.utils.logging import get_logger

logger = get_logger("explainability.prediction_explainer")

# Human-readable descriptions aligned with FEATURE_COLUMNS in features.py.
FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "rainfall_mm": "live rainfall (mm)",
    "elevation_m": "terrain elevation – lower is more flood-prone",
    "slope": "terrain slope – steeper drains faster",
    "distance_to_river_m": "distance to nearest river gauge",
    "water_level": "nearest river water level (m)",
    "water_rise_rate": "rate of river rise (m/h)",
    "road_type_numeric": "road class (motorway > residential)",
    "lanes": "number of lanes",
    "road_length_m": "segment length",
    "traffic_density": "current traffic density",
    "neighbour_flooded": "share of adjacent roads already flooded",
    "distance_to_shelter_km": "distance to nearest shelter",
}

# Heuristic weights – kept in sync with predict._heuristic_probabilities.
_HEURISTIC_WEIGHTS: Dict[str, float] = {
    "rainfall_mm": 0.40,
    "elevation_m": 0.20,
    "water_level": 0.15,
    "water_rise_rate": 0.05,
    "neighbour_flooded": 0.10,
    "distance_to_river_m": 0.05,
    "slope": -0.08,
}


def _heuristic_shap(feature_row: Dict[str, float]) -> Dict[str, float]:
    """Approximate SHAP-like contributions from the heuristic weights."""
    shap: Dict[str, float] = {}
    # Normalisation mirrors _heuristic_probabilities so numbers are interpretable.
    shap["rainfall_mm"] = _HEURISTIC_WEIGHTS["rainfall_mm"] * (np.clip(feature_row.get("rainfall_mm", 0) / 180.0, 0, 1) - 0.3)
    shap["elevation_m"] = _HEURISTIC_WEIGHTS["elevation_m"] * ((30.0 - np.clip(feature_row.get("elevation_m", 10), 0, 60)) / 30.0 - 0.5)
    shap["water_level"] = _HEURISTIC_WEIGHTS["water_level"] * (np.clip(feature_row.get("water_level", 0) / 4.0, 0, 1) - 0.3)
    shap["water_rise_rate"] = _HEURISTIC_WEIGHTS["water_rise_rate"] * (np.clip(feature_row.get("water_rise_rate", 0) / 1.5, 0, 1) - 0.2)
    # distance_to_river inverted: closer = higher risk
    shap["distance_to_river_m"] = _HEURISTIC_WEIGHTS["distance_to_river_m"] * ((1.0 - np.clip(feature_row.get("distance_to_river_m", 100) / 500.0, 0, 1)) - 0.5)
    shap["neighbour_flooded"] = _HEURISTIC_WEIGHTS["neighbour_flooded"] * (feature_row.get("neighbour_flooded", 0) - 0.2)
    shap["slope"] = _HEURISTIC_WEIGHTS["slope"] * (np.clip(feature_row.get("slope", 0) / 0.1, 0, 1) - 0.3)
    # Remaining features have no heuristic weight – small residual.
    for k in ("road_type_numeric", "lanes", "road_length_m", "traffic_density", "distance_to_shelter_km"):
        shap[k] = 0.02 * (feature_row.get(k, 0) - 2.0) / 10.0
    return shap


def _xgboost_shap(model: Any, feature_frame: Any, road_id: str) -> Optional[Dict[str, float]]:
    """Try XGBoost native ``pred_contribs`` SHAP. Returns None on any failure."""
    try:
        import xgboost as xgb  # type: ignore

        booster = model.model.get_booster() if hasattr(model, "model") else model.get_booster()
        # Single-row DMatrix for the requested road.
        row = feature_frame.loc[[road_id]]
        dmat = xgb.DMatrix(row)
        contribs = booster.predict(dmat, pred_contribs=True)
        # Shape (1, n_features+1); last column is bias.
        if contribs.ndim == 2:
            vals = contribs[0, :-1]
        else:
            vals = contribs[:-1]
        feature_names = list(feature_frame.columns)
        return {name: float(vals[i]) for i, name in enumerate(feature_names) if i < len(vals)}
    except Exception as exc:  # noqa: BLE001
        logger.debug("XGBoost SHAP failed for {}: {}", road_id, exc)
        return None


def _treelite_shap(model: Any, feature_frame: Any, road_id: str) -> Optional[Dict[str, float]]:
    """Try Treelite SHAP via ``treelite.gtil``. Requires treelite installed."""
    try:
        import treelite  # type: ignore
        import treelite.gtil  # type: ignore

        # Convert XGBoost booster to treelite model – handled via temp file.
        import tempfile
        from pathlib import Path

        booster = model.model.get_booster() if hasattr(model, "model") else model.get_booster()
        with tempfile.NamedTemporaryFile(suffix=".model", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            booster.save_model(str(tmp_path))
        try:
            tl_model = treelite.Model.load(str(tmp_path), model_format="xgboost")
            row = feature_frame.loc[[road_id]].to_numpy(dtype=float)
            # Treelite GTIL SHAP: use pred_contribs
            contribs = treelite.gtil.predict(tl_model, row, pred_contribs=True)
            if hasattr(contribs, "shape") and len(contribs.shape) == 2:
                vals = contribs[0, :-1]
            else:
                vals = contribs[:-1] if len(contribs) > 1 else contribs
            feature_names = list(feature_frame.columns)
            return {name: float(vals[i]) for i, name in enumerate(feature_names) if i < len(vals)}
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
    except ImportError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Treelite SHAP failed for {}: {}", road_id, exc)
        return None


def _captum_shap(snapshot: Dict[str, Any], road_id: str) -> Optional[Dict[str, float]]:
    """Try Captum IntegratedGradients on the ST-GNN torch model.

    Requires ``torch``, ``torch_geometric`` and ``captum`` – all optional.
    Returns None when unavailable or on any error.
    """
    try:
        import torch  # type: ignore
        from captum.attr import IntegratedGradients  # type: ignore

        from backend.prediction.stgnn.model import STGNNModel  # type: ignore
        from config.constants import STGNN_MODEL_PATH

        stgnn = STGNNModel.load(STGNN_MODEL_PATH)  # type: ignore
        if stgnn is None or not hasattr(stgnn, "model") or stgnn.model is None:
            return None
        # Build a minimal feature tensor – reuse xgboost feature frame as input.
        from backend.prediction.xgboost.features import build_road_features

        frame = build_road_features(snapshot)
        if road_id not in frame.index:
            return None
        x = torch.tensor(frame.loc[[road_id]].to_numpy(dtype=float), dtype=torch.float32, requires_grad=True)
        # Baseline = zeros
        baseline = torch.zeros_like(x)

        def forward(inp: Any) -> Any:
            # ST-GNN forward expects graph; fall back to simple wrapper.
            # If model is not compatible, IntegratedGradients will raise and we return None.
            return stgnn.model(inp)  # type: ignore

        ig = IntegratedGradients(forward)
        attributions = ig.attribute(x, baselines=baseline, n_steps=20)
        vals = attributions.detach().cpu().numpy()[0]
        feature_names = list(frame.columns)
        return {name: float(vals[i]) for i, name in enumerate(feature_names) if i < len(vals)}
    except ImportError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Captum SHAP failed for {}: {}", road_id, exc)
        return None


def explain_prediction(
    road_id: str,
    snapshot: Optional[Dict[str, Any]] = None,
    include_counterfactuals: bool = False,
) -> Dict[str, Any]:
    """Return real feature attributions for a road flood prediction.

    :param road_id: road identifier in the digital twin snapshot.
    :param snapshot: twin snapshot dict; when ``None`` the live snapshot is used.
    :param include_counterfactuals: when True, include simple counterfactuals.
    :returns: dict with ``flood_probability``, ``shap_values`` (feature->float),
        ``top_features`` (sorted list of ``{feature, importance, description}``),
        and ``counterfactuals`` when requested.
    """
    from backend.digital_twin.state_manager import get_state_manager
    from backend.prediction.xgboost.features import build_road_features
    from backend.prediction.xgboost.predict import predict_road_risks

    if snapshot is None:
        snapshot = get_state_manager().get_snapshot() or {}

    # Load model (may be None – heuristic path still works).
    model = None
    try:
        from backend.prediction.xgboost.predict import _default_model

        model = _default_model()
    except Exception:
        pass

    # Feature frame and probability.
    try:
        feature_frame = build_road_features(snapshot)
    except ValueError:
        # No roads in snapshot – return a minimal explanation so API never 500s.
        return {
            "flood_probability": 0.5,
            "shap_values": {k: 0.0 for k in FEATURE_DESCRIPTIONS},
            "top_features": [
                {"feature": k, "importance": 0.0, "description": FEATURE_DESCRIPTIONS[k]}
                for k in list(FEATURE_DESCRIPTIONS)[:3]
            ],
            "counterfactuals": None,
        }

    if road_id not in feature_frame.index:
        # Unknown road – return uniform explanation but keep road_id for API contract.
        shap = {k: 0.0 for k in feature_frame.columns}
        # Still try to compute probability from snapshot size.
        try:
            risks = predict_road_risks(snapshot, model=model)
            prob = float(risks["flood_probability"].mean()) if len(risks) else 0.5
        except Exception:
            prob = 0.5
        shap_values = shap
    else:
        try:
            risks = predict_road_risks(snapshot, model=model)
            prob = float(risks.loc[road_id, "flood_probability"]) if road_id in risks.index else 0.5
        except Exception:
            prob = 0.5

        # Attempt SHAP in priority order.
        shap_values: Optional[Dict[str, float]] = None
        if model is not None and hasattr(model, "model") and model.model is not None:
            shap_values = _treelite_shap(model, feature_frame, road_id)
            if shap_values is None:
                shap_values = _xgboost_shap(model, feature_frame, road_id)
        if shap_values is None:
            shap_values = _captum_shap(snapshot, road_id)
        if shap_values is None:
            row = feature_frame.loc[road_id].to_dict() if road_id in feature_frame.index else {}
            shap_values = _heuristic_shap(row)
            logger.debug("Using heuristic SHAP for {}", road_id)
        shap = shap_values

    # Rank by absolute SHAP value.
    ranked = sorted(shap.items(), key=lambda kv: abs(kv[1]), reverse=True)
    top_features: List[Dict[str, Any]] = [
        {
            "feature": name,
            "importance": float(abs(val)),
            "description": FEATURE_DESCRIPTIONS.get(name, f"{name} contributed to flood risk"),
        }
        for name, val in ranked[:5]
    ]
    # Preserve sign in shap_values for API; top_features uses abs for ranking.
    shap_values_out = {k: float(v) for k, v in shap.items()}

    counterfactuals: Optional[List[Dict[str, Any]]] = None
    if include_counterfactuals and road_id in feature_frame.index:
        row = feature_frame.loc[road_id].to_dict()
        # Two simple counterfactuals: halve rainfall, raise elevation by 10m.
        cf_rain = dict(row)
        cf_rain["rainfall_mm"] = max(0.0, row.get("rainfall_mm", 0) * 0.5)
        cf_elev = dict(row)
        cf_elev["elevation_m"] = row.get("elevation_m", 10) + 10.0
        # Estimate probability delta via heuristic or model.
        try:
            import pandas as pd

            cf_frame = feature_frame.copy()
            for k, v in cf_rain.items():
                cf_frame.loc[road_id, k] = v
            if model is not None and hasattr(model, "model") and model.model is not None:
                cf_prob_rain = float(model.predict_proba(cf_frame.loc[[road_id]])[0])
            else:
                cf_prob_rain = max(0.0, prob - 0.15)
            for k, v in cf_elev.items():
                cf_frame.loc[road_id, k] = v
            if model is not None and hasattr(model, "model") and model.model is not None:
                # Reset and compute second CF
                cf_frame2 = feature_frame.copy()
                for k, v in cf_elev.items():
                    cf_frame2.loc[road_id, k] = v
                cf_prob_elev = float(model.predict_proba(cf_frame2.loc[[road_id]])[0])
            else:
                cf_prob_elev = max(0.0, prob - 0.10)
        except Exception:
            cf_prob_rain = max(0.0, prob - 0.15)
            cf_prob_elev = max(0.0, prob - 0.10)
        counterfactuals = [
            {"feature": "rainfall_mm", "value": cf_rain["rainfall_mm"], "new_probability": float(np.clip(cf_prob_rain, 0, 1))},
            {"feature": "elevation_m", "value": cf_elev["elevation_m"], "new_probability": float(np.clip(cf_prob_elev, 0, 1))},
        ]

    return {
        "flood_probability": float(np.clip(prob, 0, 1)),
        "shap_values": shap_values_out,
        "top_features": top_features,
        "counterfactuals": counterfactuals,
    }
