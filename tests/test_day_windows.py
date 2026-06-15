"""Unit tests for per-day window computation incl. partial days (M2 task 2)."""

from __future__ import annotations

from datetime import date

from tripplanner.domain.budgets import day_windows
from tripplanner.domain.models import Coord, Lodging, Trip


def _trip(num_days: int, arrival: int, departure: int, ds: int = 540, de: int = 1080) -> Trip:
    return Trip(
        city="C",
        start_date=date(2026, 7, 1),
        lodging=Lodging(name="h", coord=Coord(lat=0.0, lng=0.0)),
        day_start_min=ds,
        day_end_min=de,
        places=(),
        num_days=num_days,
        arrival_min=arrival,
        departure_min=departure,
    )


def test_single_day_uses_day_window() -> None:
    assert day_windows(_trip(1, 600, 1000)) == [(540, 1080)]


def test_first_day_starts_at_arrival() -> None:
    windows = day_windows(_trip(3, 840, 660))  # arrival 14:00, departure 11:00
    assert windows[0] == (840, 1080)  # day 1: arrival -> normal day end


def test_last_day_ends_at_departure() -> None:
    windows = day_windows(_trip(3, 840, 660))
    assert windows[-1] == (540, 660)  # last day: normal start -> departure


def test_middle_days_use_full_window() -> None:
    windows = day_windows(_trip(3, 840, 660))
    assert len(windows) == 3
    assert windows[1] == (540, 1080)
