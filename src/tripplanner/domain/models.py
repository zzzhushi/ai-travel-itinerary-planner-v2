"""Domain models for the single-day routing engine (M1).

Pure data, no I/O (ADR-002). Times are **minutes since midnight** (int) so the
scheduler can do plain arithmetic; render to HH:MM only at the edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Coord:
    lat: float
    lng: float


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    category: str
    coord: Coord
    opens_min: int  # minutes since midnight
    closes_min: int


@dataclass(frozen=True)
class RankedPlace:
    place: Place
    rating: int = 3  # 1-5; M1 routes by travel only — priority lands in M3
    duration_override_min: int | None = None


@dataclass(frozen=True)
class Lodging:
    name: str
    coord: Coord


@dataclass(frozen=True)
class Trip:
    city: str
    day: date
    lodging: Lodging
    day_start_min: int  # earliest you can leave lodging
    day_end_min: int  # must be back at lodging by this time
    places: tuple[RankedPlace, ...]


@dataclass(frozen=True)
class ScheduledStop:
    place: Place
    arrive_min: int
    depart_min: int
    travel_from_prev_min: int  # travel from the previous location (lodging, for the first stop)


@dataclass(frozen=True)
class Day:
    date: date
    stops: tuple[ScheduledStop, ...]
    return_travel_min: int  # last stop -> lodging

    def total_travel_min(self) -> int:
        return sum(s.travel_from_prev_min for s in self.stops) + self.return_travel_min


@dataclass(frozen=True)
class Itinerary:
    day: Day
    unscheduled: tuple[RankedPlace, ...] = ()  # ranked places that did not fit (over-full day)

    @property
    def is_feasible(self) -> bool:
        return not self.unscheduled


# --- Multi-day (M2) --------------------------------------------------------
# Additive over the single-day engine: the multi-day orchestrator clusters
# places into day-areas and calls the M1 single-day scheduler per day. The M1
# `Trip`/`Itinerary` shapes above are unchanged.


@dataclass(frozen=True)
class MealWindow:
    """A reserved eating slot. When meal planning is on, a food pick is
    constrained to land inside [earliest_min, latest_min]."""

    name: str  # "lunch", "dinner"
    earliest_min: int
    latest_min: int  # must be seated/served by this time
    duration_min: int


@dataclass(frozen=True)
class MultiDayTrip:
    """A trip spanning num_days consecutive dates from start_date. Day 1 begins
    at arrival_min (partial first day); the last day ends at departure_min
    (partial last day); middle days use the [day_start_min, day_end_min] window."""

    city: str
    start_date: date
    num_days: int
    lodging: Lodging
    arrival_min: int  # day 1 cannot leave lodging before this
    departure_min: int  # last day must be back at lodging by this
    day_start_min: int  # normal (middle-day) window start
    day_end_min: int  # normal (middle-day) window end
    places: tuple[RankedPlace, ...]
    walking_tolerance: float = 1.0  # <1 tightens spread (less walking); >1 permits more
    plan_meals: bool = False
    meal_windows: tuple[MealWindow, ...] = ()


@dataclass(frozen=True)
class MultiDayItinerary:
    days: tuple[Day, ...]
    unscheduled: tuple[RankedPlace, ...] = ()

    @property
    def is_feasible(self) -> bool:
        return not self.unscheduled

    def total_travel_min(self) -> int:
        return sum(d.total_travel_min() for d in self.days)
