"""Trip-planning orchestrator: cluster places into day-areas, route each day.

Handles trips of any length (num_days=1 through N). For each day: partitions
places geographically via clustering.py, applies meal-window constraints,
schedules the day with the single-day TSPTW engine, and trims to the
walking-tolerance budget. Places that do not fit any day land in
`Itinerary.unscheduled` — never silently dropped.

The single-day engine (scheduler.py) is called once per day cluster.
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
            if rp.place.id in used or place.category.lower() not in FOOD_CATEGORIES:
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
    trip: Trip,
    day_date: date,
    start: int,
    end: int,
    travel_min: TravelMinutes,
) -> Itinerary:
    day_trip = Trip(
        city=trip.city,
        start_date=day_date,
        lodging=trip.lodging,
        day_start_min=start,
        day_end_min=end,
        places=tuple(day_places),
    )
    return schedule(day_trip, travel_min)


def _schedule_day_within_cap(
    day_places: list[RankedPlace],
    trip: Trip,
    day_date: date,
    start: int,
    end: int,
    cap: int,
    travel_min: TravelMinutes,
) -> tuple[Day, list[RankedPlace]]:
    """Schedule a day, then trim to the walking cap by repeatedly dropping the
    stop whose removal most reduces total travel. Returns the day and the places
    that ended up unscheduled (both trimmed and never-fit).

    The cap is a soft target: trimming always leaves at least one stop, so a day
    whose only reachable place sits beyond the cap keeps that single stop rather
    than emptying the day."""
    active = list(day_places)
    result = _schedule_day(active, trip, day_date, start, end, travel_min)

    while result.days[0].total_travel_min() > cap and len(result.days[0].stops) > 1:
        scheduled_ids = {s.place.id for s in result.days[0].stops}
        best: tuple[int, list[RankedPlace], Itinerary] | None = None
        for rp in active:
            if rp.place.id not in scheduled_ids:
                continue
            trial = [x for x in active if x.place.id != rp.place.id]
            trial_result = _schedule_day(trial, trip, day_date, start, end, travel_min)
            total = trial_result.days[0].total_travel_min()
            if best is None or total < best[0]:
                best = (total, trial, trial_result)
        if best is None:  # unreachable: the loop guard guarantees a scheduled stop
            raise RuntimeError("walking-cap trim found no scheduled stop to drop")
        _, active, result = best

    scheduled_ids = {s.place.id for s in result.days[0].stops}
    unscheduled = [rp for rp in day_places if rp.place.id not in scheduled_ids]
    return result.days[0], unscheduled


def schedule_trip(trip: Trip, travel_min: TravelMinutes) -> Itinerary:
    """Plan a trip of any length: cluster places into compact day-areas, route
    each day within its time window (honoring partial arrival/departure days),
    apply meal picks, and enforce the walking-tolerance budget. Single-day trips
    (num_days=1) skip clustering and go through the same per-day path."""
    windows = day_windows(trip)
    clusters = cluster_places(
        trip.places, trip.num_days, travel_min, threshold_min=trip.walking_neighborhood_min
    )
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
        # Report unscheduled places with their original hours, not the meal-clamped
        # ones _apply_meals may have produced.
        original_by_id = {rp.place.id: rp for rp in cluster}
        unscheduled.extend(original_by_id[rp.place.id] for rp in day_unscheduled)

    return Itinerary(days=tuple(days), unscheduled=tuple(unscheduled))
