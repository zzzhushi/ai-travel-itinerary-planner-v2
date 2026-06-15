"""M2 exit-criteria tests for the multi-day routing engine.

Deterministic and fixture-built (no network). Travel time is injected as a grid
function so the assertions are exact. These tests are immutable once committed.
"""

from __future__ import annotations

import math
from datetime import date

from tripplanner.domain.clustering import cluster_places
from tripplanner.domain.models import (
    Coord,
    Itinerary,
    Lodging,
    MealWindow,
    Place,
    RankedPlace,
    ScheduledStop,
    Trip,
)
from tripplanner.domain.multiday import schedule_trip


def _hm(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def _grid_travel(a: Coord, b: Coord) -> int:
    """10 minutes per unit of straight-line distance — exact and order-revealing."""
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


def _ranked(
    pid: str,
    x: float,
    y: float,
    opens: int = _hm(9),
    closes: int = _hm(20),
    duration: int = 30,
    category: str = "sight",
) -> RankedPlace:
    place = Place(
        id=pid,
        name=pid,
        category=category,
        coord=Coord(lat=x, lng=y),
        opens_min=opens,
        closes_min=closes,
    )
    return RankedPlace(place=place, duration_override_min=duration)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _all_stops(itin: Itinerary) -> list[ScheduledStop]:
    return [s for day in itin.days for s in day.stops]


def _find(itin: Itinerary, pid: str) -> ScheduledStop | None:
    return next((s for s in _all_stops(itin) if s.place.id == pid), None)


def _trip(
    places: tuple[RankedPlace, ...],
    *,
    num_days: int = 1,
    arrival_min: int = _hm(9),
    departure_min: int = _hm(20),
    day_start_min: int = _hm(9),
    day_end_min: int = _hm(20),
    walking_tolerance: float = 1.0,
    plan_meals: bool = False,
    meal_windows: tuple[MealWindow, ...] = (),
) -> Trip:
    return Trip(
        city="Testville",
        start_date=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=day_start_min,
        day_end_min=day_end_min,
        places=places,
        num_days=num_days,
        arrival_min=arrival_min,
        departure_min=departure_min,
        walking_tolerance=walking_tolerance,
        plan_meals=plan_meals,
        meal_windows=meal_windows,
    )


def test_days_compact() -> None:
    # Three geographically separated groups, three days: clustering must recover
    # them so each day is far tighter internally than it is from other days.
    groups = {
        "A": [(5.0, 0.0), (5.0, 1.0), (6.0, 0.0)],
        "B": [(-5.0, 0.0), (-5.0, 1.0), (-6.0, 0.0)],
        "C": [(0.0, 6.0), (1.0, 6.0), (0.0, 7.0)],
    }
    places = tuple(
        _ranked(f"{g}{i}", x, y) for g, pts in groups.items() for i, (x, y) in enumerate(pts)
    )
    clusters = cluster_places(places, num_days=3, travel_min=_grid_travel)

    assert len(clusters) == 3
    assert sorted(len(c) for c in clusters) == [3, 3, 3]

    def pair(a: RankedPlace, b: RankedPlace) -> int:
        return _grid_travel(a.place.coord, b.place.coord)

    for c in clusters:
        within = max(pair(a, b) for a in c for b in c)
        others = [p for other in clusters if other is not c for p in other]
        between = min(pair(a, b) for a in c for b in others)
        assert within < between, "each day-area must be tighter than its separation"


def test_partial_days() -> None:
    # Day 1 cannot start before a 14:00 arrival; the last day must be home by a
    # 16:00 departure. Two near clusters so both partial windows are satisfiable.
    arrival, departure = _hm(14), _hm(16)
    trip = Trip(
        city="Testville",
        start_date=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(18),
        places=(
            _ranked("A0", 5.0, 0.0),
            _ranked("A1", 5.0, 1.0),
            _ranked("B0", -5.0, 0.0),
            _ranked("B1", -5.0, 1.0),
        ),
        num_days=2,
        arrival_min=arrival,
        departure_min=departure,
    )
    itin = schedule_trip(trip, _grid_travel)

    assert len(itin.days) == 2
    first, last = itin.days[0], itin.days[-1]

    assert first.stops, "day 1 should schedule something"
    for s in first.stops:
        assert s.arrive_min >= arrival, "day 1 cannot start before arrival time"

    assert last.stops, "last day should schedule something"
    assert (
        last.stops[-1].depart_min + last.return_travel_min <= departure
    ), "last day must be back at lodging by departure time"


def test_meal_slots() -> None:
    # A restaurant sits nearest the lodging, so with meals OFF it is visited first
    # thing in the morning. With meals ON it must be slotted into the lunch window.
    lunch = MealWindow(name="lunch", earliest_min=_hm(12), latest_min=_hm(14), duration_min=60)
    places = (
        _ranked("R", 1.0, 0.0, category="restaurant", duration=60),
        _ranked("S1", 5.0, 0.0),
        _ranked("S2", 6.0, 0.0),
    )
    off = schedule_trip(_trip(places, plan_meals=False), _grid_travel)
    r_off = _find(off, "R")
    assert r_off is not None, "restaurant should be scheduled without meal planning"
    assert r_off.arrive_min < _hm(12), "nearest place is visited in the morning when meals are off"

    on = schedule_trip(_trip(places, plan_meals=True, meal_windows=(lunch,)), _grid_travel)
    r_on = _find(on, "R")
    assert r_on is not None, "the food pick must still be scheduled with meals on"
    assert lunch.earliest_min <= r_on.arrive_min, "meal pick slotted no earlier than the window"
    assert r_on.depart_min <= lunch.latest_min, "meal pick slotted no later than the window"


def test_walking_tolerance() -> None:
    # Two near places and one far place. A low tolerance trims the far place to
    # keep the day compact; a high tolerance permits the extra walking.
    places = (
        _ranked("A", 1.0, 0.0),
        _ranked("B", 2.0, 0.0),
        _ranked("C", 10.0, 0.0),
    )
    low = schedule_trip(_trip(places, walking_tolerance=0.5), _grid_travel)
    high = schedule_trip(_trip(places, walking_tolerance=3.0), _grid_travel)

    assert len(_all_stops(low)) < len(_all_stops(high)), "low tolerance trims the far stop"
    assert low.total_travel_min() < high.total_travel_min(), "low tolerance walks less"
