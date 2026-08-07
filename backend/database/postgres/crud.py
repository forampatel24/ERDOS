"""CRUD operations for operational and prediction data.

Provides generic helpers over any ORM model plus domain-specific helpers for
predictions, explanations and incidents used by the platform services.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.postgres.base import Base
from backend.database.postgres.models import (
    Explanation,
    Incident,
    Prediction,
)

ModelT = TypeVar("ModelT", bound=Base)


def create(session: Session, model: type[ModelT], **kwargs: Any) -> ModelT:
    """Create and commit a new record, returning the refreshed instance."""
    obj = model(**kwargs)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def get(session: Session, model: type[ModelT], obj_id: int) -> ModelT | None:
    """Return a record by primary key or None when not found."""
    return session.get(model, obj_id)


def list_all(session: Session, model: type[ModelT]) -> Sequence[ModelT]:
    """Return all records for a model."""
    return session.scalars(select(model)).all()


def update(
    session: Session, model: type[ModelT], obj_id: int, **kwargs: Any
) -> ModelT | None:
    """Update a record by primary key with the given fields."""
    obj = session.get(model, obj_id)
    if obj is None:
        return None
    for field, value in kwargs.items():
        setattr(obj, field, value)
    session.commit()
    session.refresh(obj)
    return obj


def delete(session: Session, model: type[ModelT], obj_id: int) -> bool:
    """Delete a record by primary key; returns True when deleted."""
    obj = session.get(model, obj_id)
    if obj is None:
        return False
    session.delete(obj)
    session.commit()
    return True


def create_prediction(session: Session, **kwargs: Any) -> Prediction:
    """Persist a new prediction row."""
    return create(session, Prediction, **kwargs)


def get_latest_predictions(
    session: Session, limit: int = 50
) -> Sequence[Prediction]:
    """Return the most recent predictions ordered by timestamp."""
    stmt = (
        select(Prediction)
        .order_by(Prediction.timestamp.desc())
        .limit(limit)
    )
    return session.scalars(stmt).all()


def get_prediction_by_road(
    session: Session, road_id: int
) -> Sequence[Prediction]:
    """Return predictions associated with a specific road."""
    stmt = (
        select(Prediction)
        .where(Prediction.road_id == road_id)
        .order_by(Prediction.timestamp.desc())
    )
    return session.scalars(stmt).all()


def create_explanation(session: Session, **kwargs: Any) -> Explanation:
    """Persist a new explanation row."""
    return create(session, Explanation, **kwargs)


def get_explanations_for_prediction(
    session: Session, prediction_id: int
) -> Sequence[Explanation]:
    """Return explanations attached to a given prediction."""
    stmt = (
        select(Explanation)
        .where(Explanation.prediction_id == prediction_id)
        .order_by(Explanation.timestamp.desc())
    )
    return session.scalars(stmt).all()


def create_incident(session: Session, **kwargs: Any) -> Incident:
    """Persist a new incident row."""
    return create(session, Incident, **kwargs)


def update_incident_status(
    session: Session, incident_id: int, status: str
) -> Incident | None:
    """Update the status of an incident by its id."""
    return update(session, Incident, incident_id, status=status)


def list_active_incidents(session: Session) -> Sequence[Incident]:
    """Return all incidents that are not closed."""
    stmt = select(Incident).where(Incident.status.is_not(None))
    return session.scalars(stmt).all()
