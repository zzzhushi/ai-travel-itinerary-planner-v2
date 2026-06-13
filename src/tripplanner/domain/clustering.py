"""Geographic day-clustering: group places into compact day-areas (M2 task 1).

Pure domain (ADR-002). The distance metric is the injected travel callable, so
the same function that costs the route also shapes the clusters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tripplanner.domain.models import Coord, RankedPlace

TravelMinutes = Callable[[Coord, Coord], int]


def cluster_places(
    places: Sequence[RankedPlace],
    num_days: int,
    travel_min: TravelMinutes,
) -> list[list[RankedPlace]]:
    """Partition places into `num_days` geographically compact groups, one per
    day. Deterministic: same input → same clustering. Empty groups are allowed
    if there are fewer places than days."""
    raise NotImplementedError
