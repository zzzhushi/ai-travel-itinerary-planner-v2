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
