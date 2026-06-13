"""Walking-skeleton use-case — one slice through the whole stack (M0).

Proves the wiring and observability end to end: it runs inside a span and emits
a fully-schema'd log line. Later milestones replace this with real use-cases.
"""

from __future__ import annotations

from tripplanner import __version__
from tripplanner.observability import Component, add_event, span


def walking_skeleton() -> dict[str, str]:
    with span("skeleton.healthcheck", component=Component.WEB):
        add_event("health requested")
        return {"status": "ok", "version": __version__}
