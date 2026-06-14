"""Unit tests for haversine travel-time estimation (M1 task 3).

The exit-criteria tests inject a grid travel function, so the real haversine is
pinned here instead.
"""

from __future__ import annotations

from tripplanner.domain.models import Coord
from tripplanner.services.travel import haversine_minutes


def test_same_point_is_zero() -> None:
    a = Coord(lat=38.72, lng=-9.14)
    assert haversine_minutes(a, a) == 0


def test_one_degree_latitude_at_walking_speed() -> None:
    # ~111 km of great-circle distance at the assumed ~5 km/h walking speed is
    # ~1334 min. Assert within tolerance so the test pins speed, not float rounding.
    a = Coord(lat=0.0, lng=0.0)
    b = Coord(lat=1.0, lng=0.0)
    minutes = haversine_minutes(a, b)
    assert 1300 <= minutes <= 1370


def test_monotonic_with_distance() -> None:
    origin = Coord(lat=0.0, lng=0.0)
    near = Coord(lat=0.1, lng=0.0)
    far = Coord(lat=0.5, lng=0.0)
    assert haversine_minutes(origin, near) < haversine_minutes(origin, far)


def test_result_is_nonnegative_int() -> None:
    minutes = haversine_minutes(Coord(lat=38.7, lng=-9.1), Coord(lat=38.8, lng=-9.2))
    assert isinstance(minutes, int)
    assert minutes >= 0
