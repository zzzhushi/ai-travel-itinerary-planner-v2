"""Canonical observability field names and enumerations, so fields never drift.

Mirrors the schema in docs/engineering-standards.md.
"""

from __future__ import annotations

from enum import StrEnum


class Component(StrEnum):
    DOMAIN = "domain"
    PLACES = "places"
    LLM = "llm"
    TRAVEL = "travel"
    REPOSITORY = "repository"
    CLI = "cli"
    WEB = "web"


class Outcome(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


# Field-name constants — the keys every log line / span carries.
CORRELATION_ID = "correlation_id"
TRACE_ID = "trace_id"
SPAN_ID = "span_id"
TRIP_ID = "trip_id"
COMPONENT = "component"
OPERATION = "operation"
DURATION_MS = "duration_ms"
OUTCOME = "outcome"
ERROR_TYPE = "error.type"
ERROR_MESSAGE = "error.message"
