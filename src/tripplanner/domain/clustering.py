"""Geographic day-clustering: group places into compact day-areas (M2 task 1).

Pure domain (ADR-002). The distance metric is the injected travel callable, so
the same function that costs the route also shapes the clusters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tripplanner.domain.models import Coord, RankedPlace

TravelMinutes = Callable[[Coord, Coord], int]


_MAX_ITERATIONS = 50


def _centroid(coords: list[Coord]) -> Coord:
    n = len(coords)
    return Coord(lat=sum(c.lat for c in coords) / n, lng=sum(c.lng for c in coords) / n)


def cluster_places(
    places: Sequence[RankedPlace],
    num_days: int,
    travel_min: TravelMinutes,
) -> list[list[RankedPlace]]:
    """Partition places into `num_days` geographically compact groups, one per
    day. Deterministic: same input → same clustering. Empty groups are allowed
    if there are fewer places than days.

    Lloyd's k-means over place coordinates, using the injected travel metric as
    the distance. Centroids are seeded deterministically from places sorted by
    coordinate (no randomness), so the result is reproducible run to run."""
    items = list(places)
    if num_days <= 1:
        return [items]
    if len(items) <= num_days:
        # One place per group, rest empty — nothing to optimize.
        return [[rp] for rp in items] + [[] for _ in range(num_days - len(items))]

    ordered = sorted(items, key=lambda rp: (rp.place.coord.lat, rp.place.coord.lng))
    # Seed one centroid per day from evenly spaced points in the sorted order.
    centroids = [ordered[i * len(ordered) // num_days].place.coord for i in range(num_days)]

    assignments: list[int] = [0] * len(items)
    for _ in range(_MAX_ITERATIONS):
        changed = False
        for idx, rp in enumerate(items):
            # Nearest centroid; ties resolved to the lowest index for determinism.
            best = min(
                range(num_days),
                key=lambda k: (travel_min(rp.place.coord, centroids[k]), k),
            )
            if best != assignments[idx]:
                assignments[idx] = best
                changed = True

        for k in range(num_days):
            members = [items[i].place.coord for i in range(len(items)) if assignments[i] == k]
            if members:
                centroids[k] = _centroid(members)
        if not changed:
            break

    return [[items[i] for i in range(len(items)) if assignments[i] == k] for k in range(num_days)]
