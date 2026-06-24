"""Geographic day-clustering: group places into compact day-areas.

Two-level algorithm:
  1. Proximity clustering (complete-linkage): forms area clusters where every
     pair of places is within `threshold_min` minutes of each other.
  2. Day packing (k-means on cluster centroids): assigns area clusters to days.

The distance metric is the injected travel callable, so the same function
that costs the route also shapes the clusters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tripplanner.domain.models import Coord, RankedPlace

TravelMinutes = Callable[[Coord, Coord], int]

_MAX_ITERATIONS = 50


def _centroid(coords: list[Coord]) -> Coord:
    n = len(coords)
    return Coord(lat=sum(c.lat for c in coords) / n, lng=sum(c.lng for c in coords) / n)


def _proximity_cluster(
    items: list[RankedPlace],
    travel_min: TravelMinutes,
    threshold_min: int,
) -> list[list[RankedPlace]]:
    """Complete-linkage hierarchical clustering with a distance cutoff.

    Merges the pair of clusters whose maximum pairwise distance is smallest
    and ≤ threshold_min, repeating until no such pair exists. Guarantees that
    within every output cluster, all pairs are ≤ threshold_min apart.

    Tie-breaking is by (max_distance, cluster_i_index, cluster_j_index) so
    the result is fully deterministic for a given input."""
    n = len(items)
    # Precompute all pairwise distances indexed by position in `items`.
    dist: list[list[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = travel_min(items[i].place.coord, items[j].place.coord)
            dist[i][j] = d
            dist[j][i] = d

    # Each cluster is a list of indices into `items`.
    clusters: list[list[int]] = [[i] for i in range(n)]

    while True:
        best: tuple[int, int, int] | None = None  # (max_linkage, ci, cj)
        for ci in range(len(clusters)):
            for cj in range(ci + 1, len(clusters)):
                max_d = max(dist[a][b] for a in clusters[ci] for b in clusters[cj])
                if max_d <= threshold_min:
                    candidate = (max_d, ci, cj)
                    if best is None or candidate < best:
                        best = candidate
        if best is None:
            break
        _, ci, cj = best
        clusters[ci] = clusters[ci] + clusters[cj]
        del clusters[cj]

    return [[items[i] for i in cluster] for cluster in clusters]


def _pack_into_days(
    area_clusters: list[list[RankedPlace]],
    num_days: int,
    travel_min: TravelMinutes,
) -> list[list[list[RankedPlace]]]:
    """Assign area clusters to days using k-means on cluster centroids.

    Returns a list of num_days day-groups, each a list of area clusters.
    Seeded deterministically from evenly-spaced cluster centroids sorted by
    coordinate — same determinism guarantee as the place-level k-means."""
    nc = len(area_clusters)
    k = num_days
    if nc <= k:
        return [[c] for c in area_clusters] + [[] for _ in range(k - nc)]

    centroids_of_clusters = [_centroid([rp.place.coord for rp in c]) for c in area_clusters]
    # Seed: evenly-spaced cluster centroids sorted by (lat, lng).
    sorted_idx = sorted(
        range(nc), key=lambda i: (centroids_of_clusters[i].lat, centroids_of_clusters[i].lng)
    )
    day_centroids = [centroids_of_clusters[sorted_idx[i * nc // k]] for i in range(k)]

    assignments: list[int] = [0] * nc
    for _ in range(_MAX_ITERATIONS):
        changed = False
        for ci in range(nc):
            best_day = min(
                range(k),
                key=lambda d: (travel_min(centroids_of_clusters[ci], day_centroids[d]), d),
            )
            if best_day != assignments[ci]:
                assignments[ci] = best_day
                changed = True

        for d in range(k):
            members = [centroids_of_clusters[ci] for ci in range(nc) if assignments[ci] == d]
            if members:
                day_centroids[d] = _centroid(members)
        if not changed:
            break

    return [[area_clusters[ci] for ci in range(nc) if assignments[ci] == d] for d in range(k)]


def cluster_places(
    places: Sequence[RankedPlace],
    num_days: int,
    travel_min: TravelMinutes,
    *,
    threshold_min: int = 30,
) -> list[list[RankedPlace]]:
    """Partition places into `num_days` day-groups using two-level clustering.

    Level 1 — proximity clustering: complete-linkage with `threshold_min` cutoff
    guarantees every pair within an area cluster is ≤ threshold_min minutes apart.

    Level 2 — day packing: k-means on area-cluster centroids assigns clusters to
    days so geographically close clusters share a day.

    Deterministic: same input → same output. Empty day-groups are allowed when
    fewer area clusters exist than days."""
    items = list(places)
    if num_days <= 1:
        return [items]

    area_clusters = _proximity_cluster(items, travel_min, threshold_min)

    if len(area_clusters) <= num_days:
        # Each area cluster gets its own day; pad with empty days.
        flat = [list(c) for c in area_clusters]
        return flat + [[] for _ in range(num_days - len(area_clusters))]

    day_groups = _pack_into_days(area_clusters, num_days, travel_min)
    return [[rp for cluster in group for rp in cluster] for group in day_groups]
