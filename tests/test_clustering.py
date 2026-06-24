"""Unit tests for day-clustering edge cases.

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


# ---------------------------------------------------------------------------
# Pairwise-threshold guarantee (complete-linkage semantics)
# ---------------------------------------------------------------------------


def test_pairwise_threshold_enforced() -> None:
    # A→B = 15 min, A→C = 30 min, B→C ≈ 34 min.
    # With threshold=15: {A,B} can merge (max=15), but adding C makes max=34 > 15.
    # B and C must therefore end up in separate clusters.
    a = _ranked("A", 0.0, 0.0)
    b = _ranked("B", 1.5, 0.0)  # A→B = round(1.5*10) = 15 min
    c = _ranked("C", 0.0, 3.0)  # A→C = 30 min, B→C ≈ 34 min
    clusters = cluster_places((a, b, c), num_days=2, travel_min=_grid_travel, threshold_min=15)
    for cids in [{rp.place.id for rp in cl} for cl in clusters]:
        assert not (
            {"B", "C"} <= cids
        ), "B and C (pairwise ≈ 34 min) must not share a cluster at threshold=15"


def test_all_nearby_places_cohere_on_one_day() -> None:
    # Four places in a line, each 0.5 units apart → pairwise ≤ 15 min; all within threshold=30.
    # With num_days=2, they should all land on the same day (the other day is empty).
    places = tuple(_ranked(f"P{i}", i * 0.5, 0.0) for i in range(4))
    clusters = cluster_places(places, num_days=2, travel_min=_grid_travel, threshold_min=30)
    assert sum(len(c) for c in clusters) == 4
    assert max(len(c) for c in clusters) == 4  # all 4 in one day


def test_two_far_groups_stay_on_separate_days() -> None:
    # Two tight groups separated by 90 min of travel — they must land on different days.
    near = [_ranked(f"A{i}", i * 0.5, 0.0) for i in range(3)]  # internal ≤ 10 min
    far = [_ranked(f"B{i}", 10.0 + i * 0.5, 0.0) for i in range(3)]  # 90+ min from near
    clusters = cluster_places(
        tuple(near + far), num_days=2, travel_min=_grid_travel, threshold_min=30
    )
    ids = [{rp.place.id for rp in c} for c in clusters]
    assert any({"A0", "A1", "A2"} <= s for s in ids), "A group must be together"
    assert any({"B0", "B1", "B2"} <= s for s in ids), "B group must be together"
