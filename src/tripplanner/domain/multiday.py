"""Multi-day routing orchestrator (M2).

Clusters places into day-areas (clustering.py), then schedules each day with the
M1 single-day engine inside that day's window — honoring partial first/last days,
optional meal windows, and the walking-tolerance budget. Pure domain (ADR-002):
travel time is the injected callable; the M1 scheduler is reused unchanged.

Mechanisms:
- partial days: each day's window comes from budgets.day_windows (task 2).
- meals: a food pick's effective hours are clamped to the meal window, so the
  existing TSPTW slots it there — no new constraint machinery (task 3).
- walking tolerance: a per-day walking budget (base * tolerance) trims the
  farthest-marginal stop until the day's travel fits the budget (task 4).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, timedelta

from tripplanner.domain.budgets import day_windows
from tripplanner.domain.clustering import cluster_places
from tripplanner.domain.durations import FOOD_CATEGORIES
from tripplanner.domain.models import (
    Coord,
    Day,
    Itinerary,
    MealWindow,
    MultiDayItinerary,
    MultiDayTrip,
    RankedPlace,
    Trip,
)
from tripplanner.domain.scheduler import schedule

TravelMinutes = Callable[[Coord, Coord], int]

# A full day's walking budget at walking_tolerance == 1.0 (minutes). The cap
# scales linearly with tolerance; below it days are trimmed to stay compact.
_BASE_DAILY_WALKING_MIN = 300


def _apply_meals(
    day_places: list[RankedPlace], meal_windows: Sequence[MealWindow]
) -> list[RankedPlace]:
    """Clamp one food pick per meal window to that window's hours, so the per-day
    TSPTW seats it inside the window. Picks distinct food places per window; skips
    a window if no remaining food place's hours overlap it."""
    result = list(day_places)
    used: set[str] = set()
    for mw in meal_windows:
        for i, rp in enumerate(result):
            place = rp.place
            if rp.place.id in used or place.category not in FOOD_CATEGORIES:
                continue
            new_open = max(place.opens_min, mw.earliest_min)
            new_close = min(place.closes_min, mw.latest_min)
            if new_open > new_close:
                continue  # hours don't overlap this meal window
            result[i] = replace(rp, place=replace(place, opens_min=new_open, closes_min=new_close))
            used.add(place.id)
            break
    return result


def _schedule_day(
    day_places: Sequence[RankedPlace],
    trip: MultiDayTrip,
    day_date: date,
    start: int,
    end: int,
    travel_min: TravelMinutes,
) -> Itinerary:
    day_trip = Trip(
        city=trip.city,
        day=day_date,
        lodging=trip.lodging,
        day_start_min=start,
        day_end_min=end,
        places=tuple(day_places),
    )
    return schedule(day_trip, travel_min)


def _schedule_day_within_cap(
    day_places: list[RankedPlace],
    trip: MultiDayTrip,
    day_date: date,
    start: int,
    end: int,
    cap: int,
    travel_min: TravelMinutes,
) -> tuple[Day, list[RankedPlace]]:
    """Schedule a day, then trim it to the walking cap by repeatedly dropping the
    stop whose removal most reduces total travel. Returns the day and the places
    that ended up unscheduled (both trimmed and never-fit)."""
    active = list(day_places)
    result = _schedule_day(active, trip, day_date, start, end, travel_min)

    while result.day.total_travel_min() > cap and len(result.day.stops) > 1:
        scheduled_ids = {s.place.id for s in result.day.stops}
        best: tuple[int, list[RankedPlace], Itinerary] | None = None
        for rp in active:
            if rp.place.id not in scheduled_ids:
                continue
            trial = [x for x in active if x.place.id != rp.place.id]
            trial_result = _schedule_day(trial, trip, day_date, start, end, travel_min)
            total = trial_result.day.total_travel_min()
            if best is None or total < best[0]:
                best = (total, trial, trial_result)
        if best is None:  # unreachable: the loop guard guarantees a scheduled stop
            raise RuntimeError("walking-cap trim found no scheduled stop to drop")
        _, active, result = best

    scheduled_ids = {s.place.id for s in result.day.stops}
    unscheduled = [rp for rp in day_places if rp.place.id not in scheduled_ids]
    return result.day, unscheduled


def schedule_trip(trip: MultiDayTrip, travel_min: TravelMinutes) -> MultiDayItinerary:
    """Produce a multi-day itinerary: compact day-areas, per-day TSPTW within the
    (possibly partial) day window, meal picks slotted into their windows when
    enabled, and each day's walking kept within the tolerance budget. Places that
    do not fit any day are returned in `unscheduled` — never silently dropped."""
    windows = day_windows(trip)
    clusters = cluster_places(trip.places, trip.num_days, travel_min)
    cap = round(_BASE_DAILY_WALKING_MIN * trip.walking_tolerance)

    days: list[Day] = []
    unscheduled: list[RankedPlace] = []
    for index, cluster in enumerate(clusters):
        day_places = list(cluster)
        if trip.plan_meals and trip.meal_windows:
            day_places = _apply_meals(day_places, trip.meal_windows)
        start, end = windows[index]
        day_date = trip.start_date + timedelta(days=index)
        day, day_unscheduled = _schedule_day_within_cap(
            day_places, trip, day_date, start, end, cap, travel_min
        )
        days.append(day)
        unscheduled.extend(day_unscheduled)

    return MultiDayItinerary(days=tuple(days), unscheduled=tuple(unscheduled))
