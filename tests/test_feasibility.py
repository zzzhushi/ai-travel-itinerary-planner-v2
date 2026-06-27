"""Unit tests for the feasibility pre-check and pushback rendering."""

from __future__ import annotations

import math
from datetime import date

from tripplanner.domain.feasibility import check_feasibility
from tripplanner.domain.models import (
    Coord,
    FixedAnchor,
    Lodging,
    Place,
    RankedPlace,
    Trip,
)
from tripplanner.domain.pushback import render_suggestions


def _hm(h: int, m: int = 0) -> int:
    return h * 60 + m


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _ranked(
    pid: str,
    x: float,
    y: float,
    *,
    duration: int = 30,
    closed_weekdays: frozenset[int] = frozenset(),
) -> RankedPlace:
    return RankedPlace(
        place=Place(
            id=pid,
            name=pid,
            category="sight",
            coord=Coord(lat=x, lng=y),
            opens_min=_hm(9),
            closes_min=_hm(20),
            closed_weekdays=closed_weekdays,
        ),
        duration_override_min=duration,
    )


def _trip(
    places: tuple[RankedPlace, ...], *, num_days: int = 1, anchors: tuple[FixedAnchor, ...] = ()
) -> Trip:
    return Trip(
        city="C",
        start_date=date(2026, 7, 1),  # Wed; +1 = Thu
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(20),
        places=places,
        num_days=num_days,
        arrival_min=_hm(9),
        departure_min=_hm(20),
        anchors=anchors,
    )


# --------------------------------------------------------------------------
# check_feasibility
# --------------------------------------------------------------------------
def test_feasible_trip_reports_no_problems() -> None:
    report = check_feasibility(_trip((_ranked("A", 1, 0), _ranked("B", 2, 0))), _grid_travel)
    assert report.feasible
    assert report.over_by == 0
    assert report.fits == report.requested == 2
    assert report.suggestions == ()


def test_over_commitment_is_infeasible_with_numbers() -> None:
    places = tuple(_ranked(f"P{i}", float(i), 0.0, duration=60) for i in range(12))
    report = check_feasibility(_trip(places), _grid_travel)
    assert not report.feasible
    assert report.over_by == report.requested - report.fits > 0
    assert any(str(report.requested) in s for s in report.suggestions)


def test_place_closed_on_all_trip_days_is_flagged() -> None:
    # Trip spans Wed(2)/Thu(3); a place closed both is closed on all days.
    closed = _ranked("SHUT", 1, 0, closed_weekdays=frozenset({2, 3}))
    report = check_feasibility(_trip((closed, _ranked("A", 1, 0)), num_days=2), _grid_travel)
    assert "SHUT" in report.closed_all_days
    assert not report.feasible


def test_place_closed_on_only_some_days_is_not_flagged() -> None:
    # Closed Monday(0) only; the trip is Wed/Thu, so it is still visitable.
    closed_mon = _ranked("MON", 1, 0, closed_weekdays=frozenset({0}))
    report = check_feasibility(_trip((closed_mon, _ranked("A", 1, 0)), num_days=2), _grid_travel)
    assert "MON" not in report.closed_all_days


def test_conflicting_anchors_make_trip_infeasible() -> None:
    a = FixedAnchor(
        place=Place("A", "A", "sight", Coord(10, 0), _hm(9), _hm(23)),
        arrival_min=_hm(19),
        duration_min=60,
    )
    b = FixedAnchor(
        place=Place("B", "B", "sight", Coord(-10, 0), _hm(9), _hm(23)),
        arrival_min=_hm(20, 5),
        duration_min=60,
    )
    report = check_feasibility(
        Trip(
            city="C",
            start_date=date(2026, 7, 1),
            lodging=_LODGING,
            day_start_min=_hm(9),
            day_end_min=_hm(23),
            places=(),
            anchors=(a, b),
        ),
        _grid_travel,
    )
    assert not report.feasible
    assert report.anchor_conflicts


# --------------------------------------------------------------------------
# render_suggestions
# --------------------------------------------------------------------------
def test_render_empty_when_feasible() -> None:
    assert (
        render_suggestions(requested=3, fits=3, over_by=0, closed_all_days=(), anchor_conflicts=())
        == ()
    )


def test_render_over_commitment_line_carries_numbers() -> None:
    out = render_suggestions(
        requested=10, fits=6, over_by=4, closed_all_days=(), anchor_conflicts=()
    )
    assert len(out) == 1
    assert "10" in out[0] and "6" in out[0] and "4" in out[0]


def test_render_swap_offer_per_closed_place() -> None:
    out = render_suggestions(
        requested=2, fits=2, over_by=0, closed_all_days=("X", "Y"), anchor_conflicts=()
    )
    assert all("swap" in s.lower() for s in out)
    assert any("X" in s for s in out) and any("Y" in s for s in out)


def test_render_passes_through_anchor_conflicts() -> None:
    out = render_suggestions(
        requested=0, fits=0, over_by=0, closed_all_days=(), anchor_conflicts=("A clashes with B",)
    )
    assert out == ("Anchor conflict: A clashes with B",)
