"""Structured prediction output object.

:class:`PredictionOutput` is the canonical prediction-layer result described in
``docs/ML_PIPELINE.md`` §18. It becomes the input to the Orchestration Engine.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PredictionOutput(BaseModel):
    """A single road's flood prediction with optional future spread.

    Fields mirror ``docs/ML_PIPELINE.md`` §18:

    - ``road_id``: identifier of the predicted road segment.
    - ``flood_probability``: probability in ``[0, 1]`` the road floods now.
    - ``predicted_accessibility``: operational ``RoadStatus`` value
      (``SAFE`` / ``MODERATE_RISK`` / ``HIGH_RISK`` / ``BLOCKED``).
    - ``future_spread``: road ids adjacent to this road that are also predicted
      to flood in the near horizon.
    - ``confidence``: model confidence in ``[0, 1]``.
    """

    model_config = ConfigDict(extra="forbid")

    road_id: str = Field(..., description="Road segment identifier")
    flood_probability: float = Field(..., ge=0.0, le=1.0, description="Flood probability in [0, 1]")
    predicted_accessibility: str = Field(..., description="Operational RoadStatus value")
    future_spread: list[str] = Field(default_factory=list, description="Adjacent roads predicted to flood")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in [0, 1]")


__all__ = ["PredictionOutput"]