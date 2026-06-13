"""Unit tests for day-clustering edge cases (M2 task 1).

The exit-criteria test pins the multi-group recovery; these pin the boundaries.
"""

from __future__ import annotations

import math

from tripplanner.domain.clustering import cluster_places
from tripplanner.domain.models import Coord, Place, RankedPlace


def _grid_travel(a: Coord, b: Coord) -> int:
    return round(math.hypot(a.lat - b.lat, a.lng - b.lng) * 10)


def _ranked(pid: str, x: float, y: float) -> RankedPlace:
    return RankedPlace(
        place=Place(
            id=pid,
            name=pid,
            category="sight",
            coord=Coord(lat=x, lng=y),
            opens_min=540,
            closes_min=1200,
        )
    )


def test_single_day_returns_all_places_in_one_group() -> None:
    places = (_ranked("A", 0, 0), _ranked("B", 9, 9))
    clusters = cluster_places(places, num_days=1, travel_min=_grid_travel)
    assert clusters == [list(places)]


def test_fewer_places_than_days_leaves_empty_groups() -> None:
    places = (_ranked("A", 0, 0), _ranked("B", 5, 5))
    clusters = cluster_places(places, num_days=4, travel_min=_grid_travel)
    assert len(clusters) == 4
    assert sum(len(c) for c in clusters) == 2  # nothing duplicated or dropped
    assert sum(1 for c in clusters if not c) == 2  # two empty days


def test_clustering_is_deterministic() -> None:
    places = tuple(_ranked(f"P{i}", i, (i * 7) % 5) for i in range(12))
    first = cluster_places(places, num_days=3, travel_min=_grid_travel)
    second = cluster_places(places, num_days=3, travel_min=_grid_travel)
    assert first == second


def test_every_place_assigned_exactly_once() -> None:
    places = tuple(_ranked(f"P{i}", i % 4, i // 4) for i in range(10))
    clusters = cluster_places(places, num_days=3, travel_min=_grid_travel)
    assigned = [rp for c in clusters for rp in c]
    assert len(assigned) == len(places)
    assert {rp.place.id for rp in assigned} == {rp.place.id for rp in places}
