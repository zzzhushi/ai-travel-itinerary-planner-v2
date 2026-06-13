"""Multi-day routing orchestrator (M2).

Clusters places into day-areas (clustering.py), then schedules each day with the
M1 single-day engine inside that day's window — honoring partial first/last days,
optional meal windows, and the walking-tolerance budget. Pure domain (ADR-002):
travel time is the injected callable; the M1 scheduler is reused unchanged.
"""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.models import Coord, MultiDayItinerary, MultiDayTrip

TravelMinutes = Callable[[Coord, Coord], int]


def schedule_trip(trip: MultiDayTrip, travel_min: TravelMinutes) -> MultiDayItinerary:
    """Produce a multi-day itinerary: compact day-areas, per-day TSPTW within the
    (possibly partial) day window, meal picks slotted into their windows when
    enabled, and each day's walking kept within the tolerance budget. Places that
    do not fit any day are returned in `unscheduled` — never silently dropped."""
    raise NotImplementedError
