"""Domain models for the routing engine.

Pure data, no I/O. Times are **minutes since midnight** (int) so the
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
    # Weekdays the place is fully closed (Mon=0..Sun=6, per date.weekday()). Empty
    # means open every day. Used to detect a place closed on all of a trip's days.
    closed_weekdays: frozenset[int] = frozenset()


@dataclass(frozen=True)
class RankedPlace:
    place: Place
    rating: int = 3  # 1-5; currently unused by the router (priority routing not yet implemented)
    duration_override_min: int | None = None


@dataclass(frozen=True)
class Lodging:
    name: str
    coord: Coord


@dataclass(frozen=True)
class MealWindow:
    """A reserved eating slot. When meal planning is on, a food pick is
    constrained to land inside [earliest_min, latest_min]."""

    name: str  # "lunch", "dinner"
    earliest_min: int
    latest_min: int  # must be seated/served by this time
    duration_min: int


@dataclass(frozen=True)
class FixedAnchor:
    """A pre-committed, fixed-time event (a dinner reservation, a timed museum
    entry). Unlike a flexible RankedPlace, the scheduler must seat it at exactly
    `arrival_min` and route everything else around it. Times are minutes since
    midnight; `arrival_min` has no date — anchors are a single-day concept in M3."""

    place: Place
    arrival_min: int  # must be AT the place at exactly this time
    duration_min: int


@dataclass(frozen=True)
class Trip:
    """A trip of one or more consecutive days.

    Single-day (num_days == 1): uses day_start_min → day_end_min; arrival_min
    and departure_min are ignored. Multi-day (num_days > 1): arrival_min
    constrains day 1, departure_min constrains the last day, middle days use
    the full [day_start_min, day_end_min] window. Both partial-day fields
    default to None so single-day construction stays concise."""

    city: str
    start_date: date
    lodging: Lodging
    day_start_min: int  # earliest you can leave lodging (normal days)
    day_end_min: int  # must be back at lodging by this time (normal days)
    places: tuple[RankedPlace, ...]
    num_days: int = 1
    arrival_min: int | None = None  # day 1 cannot leave lodging before this
    departure_min: int | None = None  # last day must return by this
    walking_neighborhood_min: int = 30  # pairwise walk-time threshold for area clustering
    walking_tolerance: float = 1.0  # <1 tightens spread (less walking); >1 permits more
    plan_meals: bool = False
    meal_windows: tuple[MealWindow, ...] = ()
    anchors: tuple[FixedAnchor, ...] = ()  # fixed-time commitments (M3: single-day only)


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
    days: tuple[Day, ...]
    unscheduled: tuple[RankedPlace, ...] = ()

    @property
    def is_feasible(self) -> bool:
        return not self.unscheduled

    def total_travel_min(self) -> int:
        return sum(d.total_travel_min() for d in self.days)
