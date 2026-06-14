"""M1 exit-criteria tests for the single-day routing engine.

Deterministic and fixture-built (no network). Travel time is injected as a grid
function so the assertions are exact. These tests are immutable once committed.
"""

from __future__ import annotations

import math
from datetime import date

from tripplanner.domain.models import (
    Coord,
    Lodging,
    Place,
    RankedPlace,
    Trip,
)
from tripplanner.domain.scheduler import schedule


def _hm(hour: int, minute: int = 0) -> int:
    """Minutes since midnight."""
    return hour * 60 + minute


def _grid_travel(a: Coord, b: Coord) -> int:
    """10 minutes per unit of straight-line distance — exact and order-revealing."""
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


def _place(pid: str, x: float, opens: int, closes: int) -> Place:
    """A place on the x-axis (lng=0) with the given window."""
    return Place(
        id=pid,
        name=pid,
        category="sight",
        coord=Coord(lat=x, lng=0.0),
        opens_min=opens,
        closes_min=closes,
    )


def _ranked(pid: str, x: float, opens: int, closes: int, duration: int) -> RankedPlace:
    return RankedPlace(place=_place(pid, x, opens, closes), duration_override_min=duration)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def test_respects_hours() -> None:
    # A is only open in the morning, B only in the afternoon: the route must wait for B.
    trip = Trip(
        city="Testville",
        day=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(18),
        places=(
            _ranked("A", x=1, opens=_hm(9), closes=_hm(12), duration=30),
            _ranked("B", x=2, opens=_hm(14), closes=_hm(18), duration=30),
        ),
    )
    itin = schedule(trip, _grid_travel)
    assert itin.is_feasible
    for stop in itin.day.stops:
        assert stop.arrive_min >= stop.place.opens_min, f"{stop.place.id} arrived before opening"
        assert stop.depart_min <= stop.place.closes_min, f"{stop.place.id} left after closing"


def test_lodging_commute() -> None:
    # One place 5 units away → 50 min each way; both legs must be accounted for.
    trip = Trip(
        city="Testville",
        day=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(18),
        places=(_ranked("A", x=5, opens=_hm(9), closes=_hm(18), duration=30),),
    )
    itin = schedule(trip, _grid_travel)
    first = itin.day.stops[0]
    assert first.travel_from_prev_min == 50  # lodging -> first stop
    assert itin.day.return_travel_min == 50  # last stop -> lodging
    assert first.arrive_min >= trip.day_start_min + 50  # couldn't arrive before travelling there
    assert first.depart_min + itin.day.return_travel_min <= trip.day_end_min  # home in time


def test_reduces_travel() -> None:
    # Places given in a zig-zag order; an optimizing route must beat the naive order.
    places = (
        _ranked("P3", x=3, opens=_hm(9), closes=_hm(18), duration=15),
        _ranked("P1", x=1, opens=_hm(9), closes=_hm(18), duration=15),
        _ranked("P2", x=2, opens=_hm(9), closes=_hm(18), duration=15),
    )
    trip = Trip(
        city="Testville",
        day=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(18),
        places=places,
    )
    # Travel if visited in the given (zig-zag) order: 0->3->1->2->0.
    coords = [_LODGING.coord, *[rp.place.coord for rp in places], _LODGING.coord]
    naive_total = sum(_grid_travel(coords[i], coords[i + 1]) for i in range(len(coords) - 1))

    itin = schedule(trip, _grid_travel)
    assert itin.is_feasible
    assert itin.day.total_travel_min() < naive_total


def test_overfull_day_flagged() -> None:
    # A 1-hour window can't hold four 30-minute visits; the rest must surface, not vanish.
    places = tuple(
        _ranked(f"P{i}", x=i, opens=_hm(9), closes=_hm(18), duration=30) for i in range(1, 5)
    )
    trip = Trip(
        city="Testville",
        day=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(10),
        places=places,
    )
    itin = schedule(trip, _grid_travel)
    assert not itin.is_feasible
    assert itin.unscheduled, "over-full day must report unscheduled places"
    assert len(itin.day.stops) + len(itin.unscheduled) == len(places)  # nothing dropped silently
    for stop in itin.day.stops:
        assert stop.depart_min <= stop.place.closes_min
