"""FastAPI application."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tripplanner.application.skeleton import walking_skeleton
from tripplanner.observability import configure_observability
from tripplanner.web.routes.schedule import router as schedule_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_observability()
    yield


app = FastAPI(title="AI Travel Itinerary Planner", lifespan=lifespan)
app.include_router(schedule_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return walking_skeleton()
