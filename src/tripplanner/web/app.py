"""FastAPI application (ADR-005). M0 ships only /health over the walking skeleton.

A per-request correlation-id middleware is deferred to a later milestone (the
Starlette context-propagation caveat makes it more than a one-liner); for now
the span ensures a correlation id exists.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tripplanner.application.skeleton import walking_skeleton
from tripplanner.observability import configure_observability


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_observability()
    yield


app = FastAPI(title="AI Travel Itinerary Planner", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return walking_skeleton()
