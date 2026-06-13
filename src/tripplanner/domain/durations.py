"""Per-place visit durations: category defaults with a per-place override (M1 task 2)."""

from __future__ import annotations

from tripplanner.domain.models import RankedPlace


def resolve_duration_min(ranked: RankedPlace) -> int:
    """Minutes to spend at a place: the per-place override, else the category default."""
    raise NotImplementedError
