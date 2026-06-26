"""Unit tests for fixed-time anchor placement and conflict detection.

These pin anchor behavior the M3 exit-criteria tests don't reach: multi-anchor
days, flexible routing around an anchor, and each distinct conflict reason
`detect_anchor_conflicts` reports.
"""

from __future__ import annotations

import math
from datetime import date

from tripplanner.application.build_schedule import build_schedule
from tripplanner.domain.models import (
    Coord,
    FixedAnchor,
    Lodging,
    Place,
    RankedPlace,
    Trip,
)
from tripplanner.domain.scheduler import detect_anchor_conflicts


def _hm(h: int, m: int = 0) -> int:
    return h * 60 + m


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _place(pid: str, x: float, y: float, *, opens: int = _hm(9), closes: int = _hm(23)) -> Place:
    return Place(
        id=pid,
        name=pid,
        category="sight",
        coord=Coord(lat=x, lng=y),
        opens_min=opens,
        closes_min=closes,
    )


def _ranked(pid: str, x: float, y: float) -> RankedPlace:
    return RankedPlace(place=_place(pid, x, y), duration_override_min=30)


def _anchor(pid: str, x: float, y: float, arrival: int, duration: int = 60) -> FixedAnchor:
    return FixedAnchor(place=_place(pid, x, y), arrival_min=arrival, duration_min=duration)


def _trip(
    places: tuple[RankedPlace, ...],
    anchors: tuple[FixedAnchor, ...],
    *,
    day_start: int = _hm(9),
    day_end: int = _hm(23),
) -> Trip:
    return Trip(
        city="C",
        start_date=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=day_start,
        day_end_min=day_end,
        places=places,
        anchors=anchors,
    )


# --------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------
def test_two_anchors_both_seated_at_their_times() -> None:
    a = _anchor("A", 1.0, 0.0, _hm(12))
    b = _anchor("B", 2.0, 0.0, _hm(15))
    itin = build_schedule(_trip((), (a, b)), _grid_travel)
    stops = {s.place.id: s for d in itin.days for s in d.stops}
    assert stops["A"].arrive_min == _hm(12)
    assert stops["B"].arrive_min == _hm(15)
    assert stops["B"].depart_min == _hm(16), "anchor departs after its duration"


def test_flexible_place_routes_into_a_segment_around_the_anchor() -> None:
    # A morning sight fits before a noon anchor; both are scheduled, sight first.
    anchor = _anchor("LUNCH", 0.5, 0.0, _hm(12))
    sight = _ranked("S", 1.0, 0.0)
    itin = build_schedule(_trip((sight,), (anchor,)), _grid_travel)
    order = [s.place.id for d in itin.days for s in d.stops]
    assert order == ["S", "LUNCH"], "the flexible morning sight precedes the noon anchor"


def test_unfittable_flexible_place_is_unscheduled_not_dropped() -> None:
    # A far place that can't fit around a tight anchor surfaces as unscheduled.
    anchor = _anchor("EVENT", 0.5, 0.0, _hm(9, 30), duration=30)
    far = _ranked("FAR", 80.0, 0.0)  # 800 min away — cannot fit the day
    itin = build_schedule(_trip((far,), (anchor,), day_end=_hm(11)), _grid_travel)
    assert "FAR" in {rp.place.id for rp in itin.unscheduled}


# --------------------------------------------------------------------------
# Conflict detection
# --------------------------------------------------------------------------
def test_no_conflict_for_a_reachable_single_anchor() -> None:
    conflicts = detect_anchor_conflicts(
        (_anchor("A", 1.0, 0.0, _hm(10)),), _LODGING.coord, _hm(9), _hm(23), _grid_travel
    )
    assert conflicts == []


def test_conflict_when_anchors_too_close_in_time_to_travel_between() -> None:
    a = _anchor("A", 10.0, 0.0, _hm(19))  # ends 20:00
    b = _anchor("B", -10.0, 0.0, _hm(20, 5))  # 200 min away, only 5 min gap
    conflicts = detect_anchor_conflicts((a, b), _LODGING.coord, _hm(9), _hm(23), _grid_travel)
    assert any("cannot travel" in c for c in conflicts)


def test_conflict_when_anchor_outside_day_window() -> None:
    early = _anchor("EARLY", 1.0, 0.0, _hm(8))  # before 09:00 day start
    conflicts = detect_anchor_conflicts((early,), _LODGING.coord, _hm(9), _hm(23), _grid_travel)
    assert any("day window" in c for c in conflicts)


def test_conflict_when_anchor_outside_its_opening_hours() -> None:
    # Place closes at 10:00 but the anchor is pinned to 18:00.
    closed = FixedAnchor(
        place=_place("X", 1.0, 0.0, closes=_hm(10)), arrival_min=_hm(18), duration_min=30
    )
    conflicts = detect_anchor_conflicts((closed,), _LODGING.coord, _hm(9), _hm(23), _grid_travel)
    assert any("opening hours" in c for c in conflicts)


def test_conflict_when_first_anchor_unreachable_from_lodging() -> None:
    far = _anchor("FAR", 100.0, 0.0, _hm(9, 30))  # 1000 min from lodging, pinned 30 min in
    conflicts = detect_anchor_conflicts((far,), _LODGING.coord, _hm(9), _hm(23), _grid_travel)
    assert any("unreachable from lodging" in c for c in conflicts)
