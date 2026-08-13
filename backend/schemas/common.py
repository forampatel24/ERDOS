"""Shared Pydantic base schemas and enums."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class APIBaseModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class TimestampMixin(APIBaseModel):
    """Mixin adding created/updated timestamps."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.now().astimezone().tzinfo))


class RequestIDMixin(APIBaseModel):
    """Mixin adding request ID for tracing."""

    request_id: UUID = Field(default_factory=uuid4)


# Generic types for paginated responses
T = TypeVar("T")


class PaginationParams(APIBaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(APIBaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        total_pages = (total + params.page_size - 1) // params.page_size
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )


class ErrorDetail(APIBaseModel):
    """Error detail object."""

    field: str
    message: str
    code: str = "VALIDATION_ERROR"


class ErrorResponse(APIBaseModel):
    """Standard error response."""

    error: "ErrorBody"


class ErrorBody(APIBaseModel):
    """Error body."""

    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: UUID


# Re-export for convenience
__all__ = [
    "APIBaseModel",
    "TimestampMixin",
    "RequestIDMixin",
    "PaginationParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorBody",
]