"""OpenTelemetry tracing and the `span` context manager (ADR-006).

`span` wraps an operation: it starts an OTel span (so logs inside carry
trace/span ids) and emits a structured completion log with `duration_ms` and
`outcome`. Use `add_event` for the less-structured narrative within a span.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode

from tripplanner.observability.context import ensure_correlation_id
from tripplanner.observability.logging import get_logger
from tripplanner.observability.schema import Component, Outcome

_TRACING_CONFIGURED = False


def configure_tracing(*, console: bool) -> None:
    """Install an SDK TracerProvider (idempotent). Without it, spans are no-ops
    and carry no valid trace id. `console` exports spans to stderr for dev."""
    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED:
        return
    provider = TracerProvider()
    if console:
        import sys

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stderr)))
    trace.set_tracer_provider(provider)
    _TRACING_CONFIGURED = True


def add_event(name: str, **attributes: Any) -> None:
    """Attach a point-in-time event to the active span (the trace narrative)."""
    trace.get_current_span().add_event(name, attributes=attributes)


@contextmanager
def span(operation: str, *, component: Component) -> Iterator[None]:
    ensure_correlation_id()
    log = get_logger(component).bind(operation=operation)
    tracer = trace.get_tracer("tripplanner")
    start = time.perf_counter()
    with tracer.start_as_current_span(operation) as otel_span:
        try:
            yield
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            otel_span.set_status(Status(StatusCode.ERROR))
            otel_span.record_exception(exc)
            log.error(
                operation,
                duration_ms=duration_ms,
                outcome=Outcome.ERROR.value,
                **{"error.type": type(exc).__name__, "error.message": str(exc)},
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(operation, duration_ms=duration_ms, outcome=Outcome.OK.value)
