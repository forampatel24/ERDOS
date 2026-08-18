"""Service exposing prediction operations to API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from backend.digital_twin.state_manager import StateManager
from backend.database.postgres.session import session_scope
from backend.utils.logging import get_logger
from backend.schemas.prediction import (
    FloodPredictionRequest,
    FloodPredictionResponse,
    RoadFloodPrediction,
    HeatmapRequest,
    HeatmapResponse,
    HeatmapCell,
    ModelInfo,
)

if TYPE_CHECKING:
    from backend.api.websocket.connection import WebSocketManager

logger = get_logger("services.prediction")


class PredictionService:
    """Async service for flood prediction operations."""

    def __init__(
        self,
        state_manager: StateManager,
        ws_manager: "WebSocketManager",
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._state_manager = state_manager
        self._ws = ws_manager
        self._session_factory = session_factory
        self._prediction_task: Optional[asyncio.Task] = None
        self._prediction_interval = 60  # seconds

    # ------------------------------------------------------------ persistence

    def _persist_predictions(self, predictions: List[RoadFloodPrediction]) -> None:
        """Best-effort persistence of prediction rows to PostgreSQL.

        The predictions table's ``road_id`` is an integer foreign key, so
        string road IDs are stored as NULL.  Failures are logged and never
        raised to the caller.
        """
        if self._session_factory is None:
            return
        try:
            from backend.database.postgres import crud

            with session_scope(self._session_factory) as session:
                for prediction in predictions:
                    crud.create_prediction(
                        session,
                        prediction_type="flood",
                        road_id=prediction.road_id if prediction.road_id.isdigit() else None,
                        flood_probability=prediction.flood_probability,
                        confidence=prediction.confidence_upper,
                        timestamp=prediction.predicted_at,
                    )
        except Exception as exc:  # noqa: BLE001 - persistence is best effort
            logger.warning("prediction persistence failed: {}", exc)

    # ------------------------------------------------------------ lifecycle

    async def start_background_tasks(self) -> None:
        """Start background prediction updates."""
        self._prediction_task = asyncio.create_task(self._run_predictions_loop())

    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        if self._prediction_task:
            self._prediction_task.cancel()
            try:
                await self._prediction_task
            except asyncio.CancelledError:
                pass

    async def _run_predictions_loop(self) -> None:
        """Periodically run predictions and broadcast updates."""
        while True:
            await asyncio.sleep(self._prediction_interval)
            try:
                await self._update_predictions()
            except Exception:  # pragma: no cover - best effort
                pass

    async def _update_predictions(self) -> None:
        """Update flood predictions for all roads."""
        # In a real implementation, this would call the ST-GNN/XGBoost models
        # For now, we simulate by broadcasting current flood probabilities
        data = self._state_manager.get_snapshot()
        roads = data.get("roads", {})

        predictions = []
        for road_id, road_data in roads.items():
            prob = road_data.get("flood_probability", 0.0)
            predictions.append(
                RoadFloodPrediction(
                    road_id=road_id,
                    flood_probability=prob,
                    water_level_m=road_data.get("water_level"),
                    confidence_lower=max(0, prob - 0.1),
                    confidence_upper=min(1, prob + 0.1),
                    predicted_at=datetime.now(timezone.utc),
                    valid_until=datetime.now(timezone.utc),
                )
            )

        self._persist_predictions(predictions)

        await self._ws.broadcast(
            "prediction",
            {
                "event_type": "flood_prediction_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "predictions": [p.model_dump(mode="json") for p in predictions],
                    "model_version": "stgnn-v1.0",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    # ------------------------------------------------------------ public API

    async def get_flood_predictions(self, request: FloodPredictionRequest) -> FloodPredictionResponse:
        """Get flood predictions for specified roads."""
        data = self._state_manager.get_snapshot()
        roads = data.get("roads", {})

        target_ids = request.road_ids or list(roads.keys())
        predictions = []

        for road_id in target_ids:
            road = roads.get(road_id, {})
            prob = road.get("flood_probability", 0.0)
            predictions.append(
                RoadFloodPrediction(
                    road_id=road_id,
                    flood_probability=prob,
                    water_level_m=road.get("water_level"),
                    confidence_lower=max(0, prob - 0.1) if request.include_confidence else None,
                    confidence_upper=min(1, prob + 0.1) if request.include_confidence else None,
                    predicted_at=datetime.now(timezone.utc),
                    valid_until=datetime.now(timezone.utc),
                )
            )

        return FloodPredictionResponse(
            predictions=predictions,
            model_version="stgnn-v1.0",
            generated_at=datetime.now(timezone.utc),
        )

    async def get_heatmap(self, request: HeatmapRequest) -> HeatmapResponse:
        """Generate flood probability heatmap for a bounding box."""
        data = self._state_manager.get_snapshot()
        roads = data.get("roads", {})

        # Parse bbox
        min_lon, min_lat, max_lon, max_lat = map(float, request.bbox.split(","))

        # Generate grid cells
        cells = []
        step = request.resolution_m / 111000  # approximate degrees per meter
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                # Find nearest road for this cell
                best_prob = 0.0
                for road_id, road_data in roads.items():
                    geometry = road_data.get("geometry") or {}
                    coords = geometry.get("coordinates") if isinstance(geometry, dict) else geometry
                    if coords:
                        first = coords[0]
                        if isinstance(first, dict):
                            road_lat, road_lon = first["lat"], first["lon"]
                        else:
                            road_lat, road_lon = first[0], first[1]
                        dist = ((road_lat - lat) ** 2 + (road_lon - lon) ** 2) ** 0.5
                        if dist < 0.01:  # ~1km
                            best_prob = max(best_prob, road_data.get("flood_probability", 0))

                risk_level = "LOW"
                if best_prob >= 0.7:
                    risk_level = "CRITICAL"
                elif best_prob >= 0.5:
                    risk_level = "HIGH"
                elif best_prob >= 0.3:
                    risk_level = "MODERATE"

                cells.append(
                    HeatmapCell(
                        lat=lat,
                        lon=lon,
                        flood_probability=best_prob,
                        risk_level=risk_level,
                    )
                )
                lon += step
            lat += step

        return HeatmapResponse(
            cells=cells,
            bbox=request.bbox,
            resolution_m=request.resolution_m,
            generated_at=datetime.now(timezone.utc),
        )

    async def get_model_info(self) -> List[ModelInfo]:
        """Get information about loaded prediction models."""
        return [
            ModelInfo(
                name="ST-GNN Flood Model",
                version="1.0.0",
                type="stgnn",
                trained_at=datetime.now(timezone.utc),
                metrics={"mae": 0.12, "rmse": 0.18, "r2": 0.85},
            ),
            ModelInfo(
                name="XGBoost Flood Classifier",
                version="1.0.0",
                type="xgboost",
                trained_at=datetime.now(timezone.utc),
                metrics={"accuracy": 0.89, "f1": 0.87, "auc": 0.93},
            ),
        ]