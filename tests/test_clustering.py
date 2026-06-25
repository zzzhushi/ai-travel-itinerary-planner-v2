"""Unit tests for geographic proximity clustering.

cluster_places is pure geometry: it knows nothing about days. These tests
verify the neighborhood-forming guarantee and boundary conditions.
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


def test_far_places_form_separate_clusters() -> None:
    # A and B are ~127 min apart (>> default threshold 30) — must be separate clusters.
    places = (_ranked("A", 0, 0), _ranked("B", 9, 9))
    clusters = cluster_places(places, travel_min=_grid_travel)
    assert len(clusters) == 2


def test_clustering_is_deterministic() -> None:
    places = tuple(_ranked(f"P{i}", i, (i * 7) % 5) for i in range(12))
    first = cluster_places(places, travel_min=_grid_travel)
    second = cluster_places(places, travel_min=_grid_travel)
    assert first == second


def test_every_place_assigned_exactly_once() -> None:
    places = tuple(_ranked(f"P{i}", i % 4, i // 4) for i in range(10))
    clusters = cluster_places(places, travel_min=_grid_travel)
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
    clusters = cluster_places((a, b, c), travel_min=_grid_travel, threshold_min=15)
    for cids in [{rp.place.id for rp in cl} for cl in clusters]:
        assert not (
            {"B", "C"} <= cids
        ), "B and C (pairwise ≈ 34 min) must not share a cluster at threshold=15"


def test_all_nearby_places_form_one_cluster() -> None:
    # Four places in a line, each 0.5 units apart → pairwise ≤ 15 min; all within threshold=30.
    # All should collapse into a single cluster.
    places = tuple(_ranked(f"P{i}", i * 0.5, 0.0) for i in range(4))
    clusters = cluster_places(places, travel_min=_grid_travel, threshold_min=30)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_two_far_groups_form_separate_clusters() -> None:
    # Two tight groups separated by 90 min of travel — must produce two clusters.
    near = [_ranked(f"A{i}", i * 0.5, 0.0) for i in range(3)]  # internal ≤ 10 min
    far = [_ranked(f"B{i}", 10.0 + i * 0.5, 0.0) for i in range(3)]  # 90+ min from near
    clusters = cluster_places(tuple(near + far), travel_min=_grid_travel, threshold_min=30)
    ids = [{rp.place.id for rp in c} for c in clusters]
    assert any({"A0", "A1", "A2"} <= s for s in ids), "A group must be together"
    assert any({"B0", "B1", "B2"} <= s for s in ids), "B group must be together"
