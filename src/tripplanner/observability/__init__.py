"""Observability: structured logging + tracing with a shared field schema."""

from __future__ import annotations

from tripplanner.observability.context import (
    bind_trip_id,
    current_correlation_id,
    current_trip_id,
    ensure_correlation_id,
    new_correlation_id,
)
from tripplanner.observability.logging import configure_observability, get_logger
from tripplanner.observability.schema import Component, Outcome
from tripplanner.observability.tracing import span

__all__ = [
    "Component",
    "Outcome",
    "bind_trip_id",
    "configure_observability",
    "current_correlation_id",
    "current_trip_id",
    "ensure_correlation_id",
    "get_logger",
    "new_correlation_id",
    "span",
]
