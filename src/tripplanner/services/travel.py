"""Travel-time estimation. v1: haversine ÷ assumed speed (pure, no I/O). v2 swaps
in the Google Routes API here without moving the call site (ADR-003)."""

from __future__ import annotations

import math

from tripplanner.domain.models import Coord

# v1 intra-city assumption: all movement is on foot. Configurable when v2 swaps
# in the Routes API (ADR-003).
_WALKING_SPEED_KMH = 5.0
_EARTH_RADIUS_KM = 6371.0


def haversine_minutes(a: Coord, b: Coord) -> int:
    """Great-circle distance between two coords, converted to whole minutes of
    travel at an assumed urban speed."""
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    distance_km = 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(h))

    hours = distance_km / _WALKING_SPEED_KMH
    return round(hours * 60)
