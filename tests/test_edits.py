"""Unit tests for deterministic trip edits and rating-aware re-solve."""

from __future__ import annotations

import math
from datetime import date

from tripplanner.application.build_schedule import build_schedule
from tripplanner.domain.edits import with_rating, with_swap
from tripplanner.domain.models import Coord, Lodging, Place, RankedPlace, Trip


def _hm(h: int, m: int = 0) -> int:
    return h * 60 + m


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


_LODGING = Lodging(name="hotel", coord=Coord(lat=0.0, lng=0.0))


def _ranked(pid: str, x: float, y: float, *, rating: int = 3, duration: int = 30) -> RankedPlace:
    return RankedPlace(
        place=Place(
            id=pid,
            name=pid,
            category="sight",
            coord=Coord(lat=x, lng=y),
            opens_min=_hm(9),
            closes_min=_hm(20),
        ),
        rating=rating,
        duration_override_min=duration,
    )


def _trip(places: tuple[RankedPlace, ...], *, walking_tolerance: float = 1.0) -> Trip:
    return Trip(
        city="C",
        start_date=date(2026, 7, 1),
        lodging=_LODGING,
        day_start_min=_hm(9),
        day_end_min=_hm(20),
        places=places,
        walking_tolerance=walking_tolerance,
    )


# --------------------------------------------------------------------------
# with_swap / with_rating (pure)
# --------------------------------------------------------------------------
def test_with_swap_removes_and_appends() -> None:
    trip = _trip((_ranked("A", 1, 0), _ranked("B", 2, 0)))
    out = with_swap(trip, remove_id="A", add=_ranked("C", 3, 0))
    ids = [rp.place.id for rp in out.places]
    assert ids == ["B", "C"]


def test_with_swap_absent_id_just_appends() -> None:
    trip = _trip((_ranked("A", 1, 0),))
    out = with_swap(trip, remove_id="ZZZ", add=_ranked("C", 3, 0))
    assert {rp.place.id for rp in out.places} == {"A", "C"}


def test_with_rating_updates_rating_and_keeps_duration_when_omitted() -> None:
    trip = _trip((_ranked("A", 1, 0, rating=3, duration=45),))
    out = with_rating(trip, place_id="A", rating=5)
    a = out.places[0]
    assert a.rating == 5
    assert a.duration_override_min == 45  # unchanged


def test_with_rating_updates_duration_when_given() -> None:
    trip = _trip((_ranked("A", 1, 0, rating=3, duration=45),))
    out = with_rating(trip, place_id="A", rating=4, duration_override_min=90)
    assert out.places[0].duration_override_min == 90


def test_with_rating_unknown_id_is_a_noop() -> None:
    trip = _trip((_ranked("A", 1, 0, rating=3),))
    out = with_rating(trip, place_id="NOPE", rating=1)
    assert out.places[0].rating == 3


def test_edits_do_not_mutate_the_original_trip() -> None:
    trip = _trip((_ranked("A", 1, 0, rating=3),))
    with_rating(trip, place_id="A", rating=1)
    with_swap(trip, remove_id="A", add=_ranked("B", 2, 0))
    assert trip.places[0].rating == 3 and [rp.place.id for rp in trip.places] == ["A"]


# --------------------------------------------------------------------------
# rating-aware re-solve
# --------------------------------------------------------------------------
def test_rating_decides_who_survives_a_capacity_trim() -> None:
    # Two far places; the walking cap keeps only one. The higher-rated survives.
    lo = _ranked("LO", 20.0, 0.0, rating=1)
    hi = _ranked("HI", 20.0, 1.0, rating=5)
    itin = build_schedule(_trip((lo, hi)), _grid_travel)
    scheduled = {s.place.id for d in itin.days for s in d.stops}
    assert "HI" in scheduled and "LO" not in scheduled


def test_reraising_a_rating_flips_the_rebuild() -> None:
    # A wins on rating first; drop A's rating below B's and the kept place flips.
    trip1 = _trip((_ranked("A", 20.0, 0.0, rating=5), _ranked("B", 20.0, 1.0, rating=3)))
    s1 = {s.place.id for d in build_schedule(trip1, _grid_travel).days for s in d.stops}
    trip2 = with_rating(trip1, place_id="A", rating=1)
    s2 = {s.place.id for d in build_schedule(trip2, _grid_travel).days for s in d.stops}
    assert s1 == {"A"} and s2 == {"B"}
