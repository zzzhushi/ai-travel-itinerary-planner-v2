"""build_schedule use-case: wire the single-day engine with observability (M1 task 5)."""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.models import Coord, Itinerary, Trip
from tripplanner.domain.scheduler import schedule
from tripplanner.observability import Component, add_event, span
from tripplanner.services.travel import haversine_minutes


def build_schedule(trip: Trip, travel_fn: Callable[[Coord, Coord], int] | None = None) -> Itinerary:
    """Route a single-day trip. Defaults to haversine travel; accepts an injected
    callable for testing (same injection seam as the domain scheduler)."""
    fn = travel_fn if travel_fn is not None else haversine_minutes
    with span("schedule.build", component=Component.DOMAIN):
        add_event("build_schedule started", places=len(trip.places))
        itin = schedule(trip, fn)
        add_event(
            "build_schedule complete",
            feasible=itin.is_feasible,
            scheduled=len(itin.day.stops),
            unscheduled=len(itin.unscheduled),
        )
    return itin
