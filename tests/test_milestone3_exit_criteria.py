"""Exit-criteria tests for Milestone 3: anchors, feasibility, rating capture, re-solve.

These five tests ARE the milestone contract (issue #5). They are written before
any feature code and are immutable: a change to one requires explicit approval,
never a silent edit to make the bar easier.

Each test imports the M3 symbol it depends on *inside the test body*. That is
deliberate: the symbols don't exist yet, so a module-level import would error at
collection and collapse all five into a single failure. Local imports let the
file collect and report each criterion as its own red test until its feature
lands in the stacked implementation PRs.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from tripplanner.application.build_schedule import build_schedule
from tripplanner.domain.models import (
    Coord,
    Itinerary,
    Lodging,
    Place,
    RankedPlace,
    ScheduledStop,
    Trip,
)


def _hm(h: int, m: int = 0) -> int:
    return h * 60 + m


def _grid_travel(a: Coord, b: Coord) -> int:
    """10 minutes per unit of straight-line distance — exact and order-revealing."""
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _place(
    pid: str,
    x: float,
    y: float,
    *,
    opens: int = _hm(9),
    closes: int = _hm(20),
    closed_weekdays: frozenset[int] = frozenset(),
) -> Place:
    kwargs: dict[str, Any] = {
        "id": pid,
        "name": pid,
        "category": "sight",
        "coord": Coord(lat=x, lng=y),
        "opens_min": opens,
        "closes_min": closes,
    }
    # Only pass the M3 field when set, so non-closed places construct on today's model.
    if closed_weekdays:
        kwargs["closed_weekdays"] = closed_weekdays
    return Place(**kwargs)


def _ranked(
    pid: str,
    x: float,
    y: float,
    *,
    opens: int = _hm(9),
    closes: int = _hm(20),
    duration: int = 30,
    closed_weekdays: frozenset[int] = frozenset(),
) -> RankedPlace:
    return RankedPlace(
        place=_place(pid, x, y, opens=opens, closes=closes, closed_weekdays=closed_weekdays),
        duration_override_min=duration,
    )


def _trip(
    places: tuple[RankedPlace, ...],
    *,
    num_days: int = 1,
    day_start: int = _hm(9),
    day_end: int = _hm(20),
    anchors: tuple[object, ...] = (),
) -> Trip:
    kwargs: dict[str, Any] = {
        "city": "Testville",
        "start_date": date(2026, 7, 1),
        "lodging": _LODGING,
        "day_start_min": day_start,
        "day_end_min": day_end,
        "places": places,
        "num_days": num_days,
        "arrival_min": day_start,
        "departure_min": day_end,
    }
    # Only pass anchors when present, so non-anchor tests construct on today's model.
    if anchors:
        kwargs["anchors"] = anchors
    return Trip(**kwargs)


def _stops(itin: Itinerary) -> list[ScheduledStop]:
    return [s for day in itin.days for s in day.stops]


def _find(itin: Itinerary, pid: str) -> ScheduledStop | None:
    return next((s for s in _stops(itin) if s.place.id == pid), None)


# ---------------------------------------------------------------------------
# 1. A fixed-time anchor lands at its time and the day routes around it.
# ---------------------------------------------------------------------------
def test_anchor_honored() -> None:
    from tripplanner.domain.models import FixedAnchor

    dinner = FixedAnchor(
        place=_place("DINNER", 0.5, 0.0, opens=_hm(11), closes=_hm(23)),
        arrival_min=_hm(19),
        duration_min=90,
    )
    sights = (_ranked("S1", 1.0, 0.0), _ranked("S2", 2.0, 0.0))
    # A 7pm dinner runs late, so the day must extend past it (and the return leg).
    itin = build_schedule(_trip(sights, anchors=(dinner,), day_end=_hm(22)), _grid_travel)

    dstop = _find(itin, "DINNER")
    assert dstop is not None, "the anchor must be scheduled"
    assert dstop.arrive_min == _hm(19), "anchor lands exactly at its fixed time"
    scheduled = {s.place.id for s in _stops(itin)}
    assert {"S1", "S2"} <= scheduled, "flexible places route around the anchor"


# ---------------------------------------------------------------------------
# 2. Mutually infeasible anchors are detected before building.
# ---------------------------------------------------------------------------
def test_anchor_infeasible() -> None:
    from tripplanner.domain.feasibility import check_feasibility
    from tripplanner.domain.models import FixedAnchor

    # A ends at 20:00 in the far north; B is pinned to 20:05 in the far south
    # (200 min away). No route can honor both — must be caught pre-build.
    a = FixedAnchor(
        place=_place("A", 10.0, 0.0, opens=_hm(9), closes=_hm(23)),
        arrival_min=_hm(19),
        duration_min=60,
    )
    b = FixedAnchor(
        place=_place("B", -10.0, 0.0, opens=_hm(9), closes=_hm(23)),
        arrival_min=_hm(20, 5),
        duration_min=60,
    )
    # Late day window so each anchor is individually fine; only the JOINT
    # sequencing (200 min of travel in a 5 min gap) is impossible.
    report = check_feasibility(_trip((), anchors=(a, b), day_end=_hm(23)), _grid_travel)

    assert not report.feasible
    assert report.anchor_conflicts, "mutually-infeasible anchors must be surfaced before building"


# ---------------------------------------------------------------------------
# 3. Over-commitment returns a pushback carrying the numbers.
# ---------------------------------------------------------------------------
def test_feasibility_pushback() -> None:
    from tripplanner.domain.feasibility import check_feasibility

    # 12 must-sees, each 60 min, in one 09:00-20:00 day (660 min): visits alone
    # exceed the day, so only a subset fits and the pushback names both counts.
    places = tuple(_ranked(f"P{i}", float(i), 0.0, duration=60) for i in range(12))
    report = check_feasibility(_trip(places), _grid_travel)

    assert not report.feasible
    assert report.requested == 12, "pushback reports how many were requested"
    assert report.fits < report.requested, "not everything fits"
    assert report.over_by == report.requested - report.fits, "over_by is the deficit"
    assert report.over_by > 0


# ---------------------------------------------------------------------------
# 4. A place closed on all available days is surfaced with a swap offer.
# ---------------------------------------------------------------------------
def test_closed_all_days() -> None:
    from tripplanner.domain.feasibility import check_feasibility

    start = date(2026, 7, 1)
    # The two weekdays this trip spans (Wed, Thu). A museum closed on both can
    # never be visited regardless of its time-of-day hours.
    trip_weekdays = frozenset((start + timedelta(days=d)).weekday() for d in range(2))
    museum = _ranked("MUSEUM", 1.0, 0.0, closed_weekdays=trip_weekdays)
    others = (_ranked("A", 1.0, 0.0), _ranked("B", 2.0, 0.0))
    report = check_feasibility(_trip((museum, *others), num_days=2), _grid_travel)

    assert "MUSEUM" in report.closed_all_days, "a place open on no trip day must be surfaced"
    assert any("swap" in s.lower() for s in report.suggestions), "with a swap offer"


# ---------------------------------------------------------------------------
# 5. Editing the trip (swap a place) and rebuilding yields a new result.
# ---------------------------------------------------------------------------
def test_resolve_after_edit() -> None:
    from tripplanner.domain.edits import with_swap

    far = _ranked("FAR", 30.0, 0.0)  # too far to fit alongside the near pair
    trip1 = _trip((_ranked("A", 1.0, 0.0), _ranked("B", 2.0, 0.0), far))
    itin1 = build_schedule(trip1, _grid_travel)

    near = _ranked("NEAR", 3.0, 0.0)
    trip2 = with_swap(trip1, remove_id="FAR", add=near)
    itin2 = build_schedule(trip2, _grid_travel)

    ids1 = {s.place.id for s in _stops(itin1)}
    ids2 = {s.place.id for s in _stops(itin2)}
    assert ids1 != ids2, "swapping a place and rebuilding yields a different plan"
    assert "NEAR" in ids2 and "FAR" not in ids2, "the swap is reflected in the rebuild"
