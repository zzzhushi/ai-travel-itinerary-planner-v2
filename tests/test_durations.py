"""Unit tests for visit-duration resolution (M1 task 2).

The category-default behavior is not pinned by the exit-criteria tests (those
always set an override), so it is pinned here.
"""

from __future__ import annotations

from tripplanner.domain.durations import resolve_duration_min
from tripplanner.domain.models import Coord, Place, RankedPlace


def _ranked(category: str, override: int | None = None) -> RankedPlace:
    place = Place(
        id="p",
        name="p",
        category=category,
        coord=Coord(lat=0.0, lng=0.0),
        opens_min=9 * 60,
        closes_min=18 * 60,
    )
    return RankedPlace(place=place, duration_override_min=override)


def test_override_takes_precedence() -> None:
    # An explicit override wins even when the category has a default.
    assert resolve_duration_min(_ranked("museum", override=20)) == 20


def test_known_category_default() -> None:
    # A viewpoint defaults to a short visit; a museum to a long one (PRD examples).
    assert resolve_duration_min(_ranked("viewpoint")) == 30
    assert resolve_duration_min(_ranked("museum")) == 90


def test_unknown_category_falls_back() -> None:
    # An unrecognized category yields the generic default, never an error.
    assert resolve_duration_min(_ranked("speakeasy")) == 60
