"""Per-place visit durations: category defaults with a per-place override."""

from __future__ import annotations

from tripplanner.domain.models import RankedPlace

_CATEGORY_DEFAULTS: dict[str, int] = {
    "viewpoint": 30,
    "miradouro": 30,
    "museum": 90,
    "sight": 60,
    "landmark": 60,
    "park": 60,
    "restaurant": 60,
    "cafe": 45,
    "market": 45,
}

_FALLBACK_MIN = 60

# Categories eligible to fill a meal window.
FOOD_CATEGORIES: frozenset[str] = frozenset({"restaurant", "cafe"})

def resolve_duration_min(ranked: RankedPlace) -> int:
    """Minutes to spend at a place: the per-place override, else the category default."""
    if ranked.duration_override_min is not None:
        return ranked.duration_override_min
    return _CATEGORY_DEFAULTS.get(ranked.place.category.lower(), _FALLBACK_MIN)
