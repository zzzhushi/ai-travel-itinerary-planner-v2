"""Tests for the itinerary presenter."""

from __future__ import annotations

from datetime import date

from tripplanner.application.presenters import format_itinerary
from tripplanner.domain.models import Coord, Day, Itinerary, Place, RankedPlace


def _place(pid: str) -> Place:
    return Place(
        id=pid,
        name=pid,
        category="sight",
        coord=Coord(lat=0.0, lng=0.0),
        opens_min=9 * 60,
        closes_min=18 * 60,
    )


def _empty_itinerary() -> Itinerary:
    return Itinerary(
        days=(Day(date=date(2026, 7, 1), stops=(), return_travel_min=0),),
    )


def _infeasible_itinerary() -> Itinerary:
    unscheduled = (RankedPlace(place=_place("A")), RankedPlace(place=_place("B")))
    return Itinerary(
        days=(Day(date=date(2026, 7, 1), stops=(), return_travel_min=0),),
        unscheduled=unscheduled,
    )


def test_format_itinerary_zero_stops_feasible() -> None:
    output = format_itinerary(_empty_itinerary())
    assert "Day 1" in output
    assert "2026-07-01" in output
    assert "no stops" in output
    assert "Total travel: 0 min" in output
    assert "Did not fit" not in output


def test_format_itinerary_zero_stops_with_unscheduled() -> None:
    output = format_itinerary(_infeasible_itinerary())
    assert "Did not fit (2)" in output
    assert "A" in output
    assert "B" in output


def test_format_itinerary_uses_hhmm_not_raw_minutes() -> None:
    # Ensures times render as HH:MM, not as raw integer minutes.
    from tripplanner.domain.models import ScheduledStop

    stop = ScheduledStop(
        place=_place("P"),
        arrive_min=9 * 60 + 30,  # 09:30
        depart_min=10 * 60,  # 10:00
        travel_from_prev_min=30,
    )
    itin = Itinerary(
        days=(Day(date=date(2026, 7, 1), stops=(stop,), return_travel_min=20),),
    )
    output = format_itinerary(itin)
    assert "09:30" in output
    assert "10:00" in output
    assert "570" not in output  # 9*60+30 raw minutes must not appear
