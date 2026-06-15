"""build_schedule use-case: wire the single-day engine with observability."""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.models import Coord, Itinerary, MultiDayItinerary, MultiDayTrip, Trip
from tripplanner.domain.multiday import schedule_trip
from tripplanner.domain.scheduler import schedule
from tripplanner.observability import Component, add_event, span
from tripplanner.services.travel import haversine_minutes

TravelFn = Callable[[Coord, Coord], int]

def build_schedule(trip: Trip, travel_fn: TravelFn | None = None) -> Itinerary:
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


def build_multiday_schedule(
    trip: MultiDayTrip, travel_fn: TravelFn | None = None
) -> MultiDayItinerary:
    """Route a multi-day trip. Defaults to haversine travel; accepts an injected
    callable for testing."""
    fn = travel_fn if travel_fn is not None else haversine_minutes
    with span("schedule.build_multiday", component=Component.DOMAIN):
        add_event("build_multiday_schedule started", days=trip.num_days, places=len(trip.places))
        itin = schedule_trip(trip, fn)
        add_event(
            "build_multiday_schedule complete",
            feasible=itin.is_feasible,
            days=len(itin.days),
            scheduled=sum(len(d.stops) for d in itin.days),
            unscheduled=len(itin.unscheduled),
        )
    return itin
