"""structlog configuration: JSON logs carrying the observability field schema.

A failed run must be diagnosable from these logs alone (ADR-006). Logs go to
stdout and `logs/app.jsonl`; tests pass a `stream` to capture them. File
rotation is not yet implemented — when it lands, switch this to stdlib logging with
a RotatingFileHandler and retire `_Tee`.
"""

from __future__ import annotations

import atexit
import logging
import sys
from typing import TextIO, cast

import structlog
from opentelemetry import trace
from structlog.typing import EventDict, FilteringBoundLogger, WrappedLogger

from tripplanner.config import load_settings
from tripplanner.observability.context import current_trip_id, ensure_correlation_id
from tripplanner.observability.schema import (
    COMPONENT,
    CORRELATION_ID,
    SPAN_ID,
    TRACE_ID,
    TRIP_ID,
    Component,
)

_LEVELS = logging.getLevelNamesMapping()
_log_file: TextIO | None = None


class _Tee:
    """Minimal multiplexing sink — writes each log line to several streams."""

    def __init__(self, *streams: TextIO) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def _close_log_file() -> None:
    """Flush + close the process log file (on reconfigure and at exit)."""
    global _log_file
    if _log_file is not None:
        _log_file.flush()
        _log_file.close()
        _log_file = None


atexit.register(_close_log_file)


def _add_context(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Inject the per-run correlation id and trip id (the threads you follow)."""
    event_dict.setdefault(CORRELATION_ID, ensure_correlation_id())
    trip = current_trip_id()
    if trip is not None:
        event_dict.setdefault(TRIP_ID, trip)
    return event_dict


def _add_trace_ids(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Inject trace/span ids from the active OpenTelemetry span, if any."""
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        event_dict[TRACE_ID] = format(ctx.trace_id, "032x")
        event_dict[SPAN_ID] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging(stream: TextIO | None = None) -> None:
    settings = load_settings()
    level = _LEVELS.get(settings.log_level.upper(), logging.INFO)
    if stream is None:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        _close_log_file()  # release any handle from a previous configure
        global _log_file
        _log_file = settings.log_file.open("a", encoding="utf-8")
        sink: TextIO = cast("TextIO", _Tee(sys.stdout, _log_file))
    else:
        sink = stream
    structlog.configure(
        processors=[
            _add_context,
            _add_trace_ids,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sink),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=False,
    )


def get_logger(component: Component) -> FilteringBoundLogger:
    """A logger bound to its component (one of the schema's component values)."""
    return cast("FilteringBoundLogger", structlog.get_logger().bind(**{COMPONENT: component.value}))
