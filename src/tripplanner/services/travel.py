"""Travel-time estimation. v1: haversine ÷ assumed speed (pure, no I/O). v2 swaps
in the Google Routes API here without moving the call site (ADR-003)."""

from __future__ import annotations

from tripplanner.domain.models import Coord


def haversine_minutes(a: Coord, b: Coord) -> int:
    """Great-circle distance between two coords, converted to whole minutes of
    travel at an assumed urban speed. Implemented in M1 task 3."""
    raise NotImplementedError
