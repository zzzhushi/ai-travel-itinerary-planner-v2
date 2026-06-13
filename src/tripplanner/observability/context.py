"""Per-run context — correlation id and trip id — carried via contextvars.

Every log line and span inherits these so a single run is followable end to end.
"""

from __future__ import annotations

import contextvars
import uuid

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_trip_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trip_id", default=None)


def new_correlation_id() -> str:
    """Generate and bind a fresh correlation id for this run/request."""
    cid = uuid.uuid4().hex
    _correlation_id.set(cid)
    return cid


def ensure_correlation_id() -> str:
    """Return the current correlation id, generating one if none is bound."""
    cid = _correlation_id.get()
    return cid if cid is not None else new_correlation_id()


def current_correlation_id() -> str | None:
    return _correlation_id.get()


def bind_trip_id(trip_id: str) -> None:
    _trip_id.set(trip_id)


def current_trip_id() -> str | None:
    return _trip_id.get()
