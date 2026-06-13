"""structlog configuration. Implemented in M0 task 3."""

from __future__ import annotations

from typing import IO

import structlog

from tripplanner.observability.schema import Component


def configure_observability(stream: IO[str] | None = None) -> None:
    raise NotImplementedError


def get_logger(component: Component) -> structlog.stdlib.BoundLogger:
    raise NotImplementedError
