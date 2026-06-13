"""Single-day routing: order stops to minimize travel within all constraints (M1 task 4).

Pure domain. Travel time is an injected callable (haversine lives in services/, and
domain imports nothing from services — ADR-002).
"""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.models import Coord, Itinerary, Trip

TravelMinutes = Callable[[Coord, Coord], int]


def schedule(trip: Trip, travel_min: TravelMinutes) -> Itinerary:
    """Route the trip's places into a single day respecting opening hours, visit
    durations, the day window, and the lodging commute. Places that can't fit are
    returned in `Itinerary.unscheduled` (never silently dropped)."""
    raise NotImplementedError
