"""Observability: structured logging + tracing with a shared field schema (ADR-006)."""

from __future__ import annotations

from typing import TextIO

from tripplanner.observability.context import (
    bind_trip_id,
    current_correlation_id,
    current_trip_id,
    ensure_correlation_id,
    new_correlation_id,
)
from tripplanner.observability.logging import configure_logging, get_logger
from tripplanner.observability.schema import Component, Outcome
from tripplanner.observability.tracing import add_event, configure_tracing, span


def configure_observability(stream: TextIO | None = None) -> None:
    """Wire tracing + logging. Pass a stream in tests; None → stdout + log file."""
    configure_tracing(console=stream is None)
    configure_logging(stream)


__all__ = [
    "Component",
    "Outcome",
    "add_event",
    "bind_trip_id",
    "configure_observability",
    "current_correlation_id",
    "current_trip_id",
    "ensure_correlation_id",
    "get_logger",
    "new_correlation_id",
    "span",
]
