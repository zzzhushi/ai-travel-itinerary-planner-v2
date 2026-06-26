"""Geographic proximity clustering: group places into compact walkable neighborhoods.

Pure geometry — no concept of days or trip structure. Returns however many area
clusters the geography produces; the caller decides how to assign them to days.

The distance metric is the injected travel callable, so the same function
that costs the route also shapes the clusters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tripplanner.domain.models import Coord, RankedPlace

TravelMinutes = Callable[[Coord, Coord], int]


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


def cluster_places(
    places: Sequence[RankedPlace],
    travel_min: TravelMinutes,
    *,
    threshold_min: int = 30,
) -> list[list[RankedPlace]]:
    """Partition places into geographically compact area clusters.

    Uses complete-linkage hierarchical clustering with `threshold_min` as the
    distance cutoff, guaranteeing every pair within an output cluster is
    ≤ threshold_min minutes apart. Returns a variable number of clusters
    (one per distinct walkable neighborhood found in the data).

    Deterministic: same input → same output."""
    return _proximity_cluster(list(places), travel_min, threshold_min)
