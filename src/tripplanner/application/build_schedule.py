"""Schedule-build use-case: wire the routing engine with observability."""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.models import Coord, Itinerary, Trip
from tripplanner.domain.planner import schedule_trip
from tripplanner.observability import Component, add_event, span
from tripplanner.services.travel import haversine_minutes

TravelFn = Callable[[Coord, Coord], int]


def build_schedule(trip: Trip, travel_fn: TravelFn | None = None) -> Itinerary:
    """Route a trip (single- or multi-day). Defaults to haversine travel; accepts
    an injected callable for testing."""
    fn = travel_fn if travel_fn is not None else haversine_minutes
    with span("schedule.build", component=Component.DOMAIN):
        add_event("build_schedule started", days=trip.num_days, places=len(trip.places))
        itin = schedule_trip(trip, fn)
        add_event(
            "build_schedule complete",
            feasible=itin.is_feasible,
            days=len(itin.days),
            scheduled=sum(len(d.stops) for d in itin.days),
            unscheduled=len(itin.unscheduled),
        )
    return itin
