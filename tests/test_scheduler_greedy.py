"""Regression test for the greedy selection criterion (M1 ship review).

The original greedy picked the nearest place by travel alone, which could pick a
very close but late-opening place first, burn the day waiting, and strand a place
that a different order would have fit. Selecting by earliest feasible departure
fixes this. This test fails on the nearest-by-travel version.
"""

from __future__ import annotations

import math
from datetime import date

from tripplanner.domain.models import Coord, Lodging, Place, RankedPlace, Trip
from tripplanner.domain.scheduler import schedule


def _hm(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


def test_late_opener_does_not_strand_an_early_place() -> None:
    # A is ~1 min from lodging but opens only at 16:00; B is 20 min away and open
    # all day. Picking A first (nearest) waits until 16:00 and leaves B unable to
    # fit; the feasible order is B then A. Both must be scheduled.
    trip = Trip(
        city="Testville",
        day=date(2026, 7, 1),
        lodging=Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0)),
        day_start_min=_hm(9),
        day_end_min=_hm(18),
        places=(
            RankedPlace(
                place=Place(
                    id="A",
                    name="A",
                    category="sight",
                    coord=Coord(lat=0.1, lng=0.0),
                    opens_min=_hm(16),
                    closes_min=_hm(18),
                ),
                duration_override_min=30,
            ),
            RankedPlace(
                place=Place(
                    id="B",
                    name="B",
                    category="sight",
                    coord=Coord(lat=2.0, lng=0.0),
                    opens_min=_hm(9),
                    closes_min=_hm(18),
                ),
                duration_override_min=60,
            ),
        ),
    )
    itin = schedule(trip, _grid_travel)
    assert itin.is_feasible, "both places fit in order B then A"
    scheduled_ids = [stop.place.id for stop in itin.day.stops]
    assert scheduled_ids == ["B", "A"]
