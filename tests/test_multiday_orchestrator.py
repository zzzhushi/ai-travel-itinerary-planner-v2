"""Unit tests for multi-day orchestration edges (M2 tasks 3, 4, orchestrator).

The exit-criteria tests pin the headline behaviors; these pin invariants and
boundaries the exit tests don't reach.
"""

from __future__ import annotations

import math
from datetime import date

from tripplanner.domain.models import (
    Coord,
    Lodging,
    MealWindow,
    MultiDayTrip,
    Place,
    RankedPlace,
)
from tripplanner.domain.multiday import schedule_trip


def _hm(h: int, m: int = 0) -> int:
    return h * 60 + m


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


def _ranked(
    pid: str,
    x: float,
    y: float,
    *,
    opens: int = _hm(9),
    closes: int = _hm(20),
    duration: int = 30,
    category: str = "sight",
) -> RankedPlace:
    return RankedPlace(
        place=Place(
            id=pid,
            name=pid,
            category=category,
            coord=Coord(lat=x, lng=y),
            opens_min=opens,
            closes_min=closes,
        ),
        duration_override_min=duration,
    )


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _trip(
    places: tuple[RankedPlace, ...],
    *,
    num_days: int = 1,
    plan_meals: bool = False,
    meal_windows: tuple[MealWindow, ...] = (),
    walking_tolerance: float = 1.0,
) -> MultiDayTrip:
    return MultiDayTrip(
        city="C",
        start_date=date(2026, 7, 1),
        num_days=num_days,
        lodging=_LODGING,
        arrival_min=_hm(9),
        departure_min=_hm(20),
        day_start_min=_hm(9),
        day_end_min=_hm(20),
        places=places,
        plan_meals=plan_meals,
        meal_windows=meal_windows,
        walking_tolerance=walking_tolerance,
    )


def test_nothing_dropped_silently() -> None:
    places = tuple(_ranked(f"P{i}", i, 0) for i in range(6))
    itin = schedule_trip(_trip(places, num_days=2), _grid_travel)
    scheduled = {s.place.id for day in itin.days for s in day.stops}
    dropped = {rp.place.id for rp in itin.unscheduled}
    assert scheduled.isdisjoint(dropped)
    assert scheduled | dropped == {rp.place.id for rp in places}


def test_produces_one_entry_per_day_even_when_empty() -> None:
    # Two places, three days: clustering leaves one empty day; still three days out.
    places = (_ranked("A", 0, 0), _ranked("B", 9, 9))
    itin = schedule_trip(_trip(places, num_days=3), _grid_travel)
    assert len(itin.days) == 3


def test_dinner_only_restaurant_is_not_forced_into_lunch() -> None:
    # A restaurant open only in the evening cannot fill a midday lunch window; its
    # hours don't overlap, so it is left unconstrained (scheduled by normal routing).
    lunch = MealWindow(name="lunch", earliest_min=_hm(12), latest_min=_hm(14), duration_min=60)
    places = (
        _ranked("R", 1, 0, opens=_hm(18), closes=_hm(22), duration=60, category="restaurant"),
        _ranked("S", 5, 0),
    )
    itin = schedule_trip(_trip(places, plan_meals=True, meal_windows=(lunch,)), _grid_travel)
    r = next((s for day in itin.days for s in day.stops if s.place.id == "R"), None)
    # If scheduled at all, it must be in the evening — never clamped into the lunch slot.
    if r is not None:
        assert r.arrive_min >= _hm(18)


def test_default_tolerance_keeps_a_normal_compact_day() -> None:
    # Three nearby places at the default tolerance fit without any trimming.
    places = (_ranked("A", 1, 0), _ranked("B", 2, 0), _ranked("C", 3, 0))
    itin = schedule_trip(_trip(places), _grid_travel)
    assert itin.is_feasible
    assert len({s.place.id for day in itin.days for s in day.stops}) == 3
