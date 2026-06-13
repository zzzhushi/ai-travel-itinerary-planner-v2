"""OpenTelemetry tracing + the `span` context manager. Implemented in M0 task 4."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from tripplanner.observability.schema import Component


@contextmanager
def span(operation: str, *, component: Component) -> Iterator[None]:
    raise NotImplementedError
    yield  # pragma: no cover - unreachable stub marker
