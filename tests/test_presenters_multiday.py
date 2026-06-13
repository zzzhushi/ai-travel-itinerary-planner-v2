"""Tests for the multi-day itinerary presenter (M2 task 5)."""

from __future__ import annotations

from datetime import date

from tripplanner.application.presenters import format_multiday
from tripplanner.domain.models import (
    Coord,
    Day,
    MultiDayItinerary,
    Place,
    RankedPlace,
    ScheduledStop,
)


def _place(pid: str) -> Place:
    return Place(
        id=pid,
        name=pid,
        category="sight",
        coord=Coord(lat=0.0, lng=0.0),
        opens_min=540,
        closes_min=1200,
    )


def _day(d: date, *stops: ScheduledStop, return_travel: int = 10) -> Day:
    return Day(date=d, stops=tuple(stops), return_travel_min=return_travel)


def _stop(pid: str, arrive: int, depart: int, travel: int) -> ScheduledStop:
    return ScheduledStop(
        place=_place(pid), arrive_min=arrive, depart_min=depart, travel_from_prev_min=travel
    )


def test_multiday_has_a_header_per_day() -> None:
    itin = MultiDayItinerary(
        days=(
            _day(date(2026, 7, 1), _stop("Castle", 9 * 60 + 30, 10 * 60, 20)),
            _day(date(2026, 7, 2), _stop("Museum", 10 * 60, 11 * 60, 15)),
        )
    )
    out = format_multiday(itin)
    assert "Day 1" in out
    assert "Day 2" in out
    assert "2026-07-01" in out
    assert "2026-07-02" in out


def test_multiday_renders_times_as_hhmm_and_place_names() -> None:
    itin = MultiDayItinerary(
        days=(_day(date(2026, 7, 1), _stop("Castle", 9 * 60 + 30, 10 * 60, 20)),)
    )
    out = format_multiday(itin)
    assert "09:30" in out
    assert "10:00" in out
    assert "Castle" in out
    assert "570" not in out  # raw minutes must not leak


def test_multiday_lists_unscheduled_at_the_end() -> None:
    itin = MultiDayItinerary(
        days=(_day(date(2026, 7, 1), _stop("Castle", 9 * 60 + 30, 10 * 60, 20)),),
        unscheduled=(RankedPlace(place=_place("Aquarium")),),
    )
    out = format_multiday(itin)
    assert "Did not fit (1)" in out
    assert "Aquarium" in out


def test_multiday_empty_day_is_still_shown() -> None:
    itin = MultiDayItinerary(days=(_day(date(2026, 7, 1)),))
    out = format_multiday(itin)
    assert "Day 1" in out
