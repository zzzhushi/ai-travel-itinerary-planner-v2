"""Single-day routing: order stops to minimize travel within all constraints.

Pure domain. Travel time is an injected callable (haversine lives in services/, and
domain imports nothing from services — ADR-002).

Algorithm (ADR-003): greedy nearest-feasible insertion to get an initial ordering,
then 2-opt local search to reduce total travel without violating time windows.
Hard time-window anchors (fixed-time events) are not yet modelled.
"""

from __future__ import annotations

from collections.abc import Callable

from tripplanner.domain.durations import resolve_duration_min
from tripplanner.domain.models import (
    Coord,
    Day,
    Itinerary,
    RankedPlace,
    ScheduledStop,
    Trip,
)

TravelMinutes = Callable[[Coord, Coord], int]


def _try_schedule(
    ordered: list[RankedPlace],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> tuple[list[ScheduledStop], int] | None:
    """Simulate the route in the given order. Returns (stops, return_travel_min) if
    every time-window and day-budget constraint is satisfied, None otherwise."""
    stops: list[ScheduledStop] = []
    current_time = day_start
    current_coord = lodging

    for rp in ordered:
        place = rp.place
        travel = travel_min(current_coord, place.coord)
        # Wait at the place if we arrive before it opens.
        arrive = max(current_time + travel, place.opens_min)
        duration = resolve_duration_min(rp)
        depart = arrive + duration

        if depart > place.closes_min:
            return None
        # Ensure there is still time to return to lodging before day end.
        if depart + travel_min(place.coord, lodging) > day_end:
            return None

        stops.append(
            ScheduledStop(
                place=place,
                arrive_min=arrive,
                depart_min=depart,
                travel_from_prev_min=travel,
            )
        )
        current_time = depart
        current_coord = place.coord

    return_travel = travel_min(current_coord, lodging) if stops else 0
    return stops, return_travel


def _total_travel(stops: list[ScheduledStop], return_travel: int) -> int:
    return sum(s.travel_from_prev_min for s in stops) + return_travel


def _greedy(
    candidates: list[RankedPlace],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> tuple[list[RankedPlace], list[RankedPlace]]:
    """Nearest-feasible greedy: at each step pick the reachable place with the
    smallest travel cost. Returns (scheduled_order, unscheduled)."""
    remaining = list(candidates)
    ordered: list[RankedPlace] = []
    current_time = day_start
    current_coord = lodging

    while remaining:
        # (rp, travel, depart) of the best feasible next stop found so far.
        best: tuple[RankedPlace, int, int] | None = None

        for rp in remaining:
            place = rp.place
            travel = travel_min(current_coord, place.coord)
            arrive = max(current_time + travel, place.opens_min)
            depart = arrive + resolve_duration_min(rp)

            if depart > place.closes_min:
                continue
            if depart + travel_min(place.coord, lodging) > day_end:
                continue

            # Choose the earliest-finishing feasible stop, not the nearest: a
            # nearby but late-opening place would burn the morning waiting and
            # strand others. 2-opt then minimizes travel over the chosen set.
            # Ties broken by smaller travel to keep the route compact.
            if best is None or depart < best[2] or (depart == best[2] and travel < best[1]):
                best = (rp, travel, depart)

        if best is None:
            break  # Nothing left can fit; remaining all go to unscheduled.

        best_rp, _, best_depart = best
        ordered.append(best_rp)
        remaining.remove(best_rp)
        current_time = best_depart
        current_coord = best_rp.place.coord

    return ordered, remaining


def _two_opt(
    order: list[RankedPlace],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> list[RankedPlace]:
    """2-opt: reverse sub-sequences and keep the swap when it reduces total travel
    and every time-window constraint stays satisfied. Repeats until no improvement."""
    if len(order) < 2:
        return order

    improved = True
    while improved:
        improved = False
        cur = _try_schedule(order, lodging, day_start, day_end, travel_min)
        # The incoming order is always greedy-feasible; raise (not assert, which -O
        # strips) if that invariant is ever broken rather than crash on None unpack.
        if cur is None:
            raise RuntimeError("2-opt received an infeasible base order")
        cur_travel = _total_travel(*cur)

        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                candidate = order[:i] + list(reversed(order[i : j + 1])) + order[j + 1 :]
                result = _try_schedule(candidate, lodging, day_start, day_end, travel_min)
                if result is None:
                    continue
                if _total_travel(*result) < cur_travel:
                    order = candidate
                    improved = True
                    break
            if improved:
                break

    return order


def schedule(trip: Trip, travel_min: TravelMinutes) -> Itinerary:
    """Route the trip's places into a single day respecting opening hours, visit
    durations, the day window, and the lodging commute. Places that can't fit are
    returned in `Itinerary.unscheduled` (never silently dropped)."""
    lodging = trip.lodging.coord

    ordered, unscheduled = _greedy(
        list(trip.places), lodging, trip.day_start_min, trip.day_end_min, travel_min
    )
    ordered = _two_opt(ordered, lodging, trip.day_start_min, trip.day_end_min, travel_min)

    result = _try_schedule(ordered, lodging, trip.day_start_min, trip.day_end_min, travel_min)
    # _try_schedule can only fail here if travel_min is non-deterministic (haversine is not).
    # Raise explicitly so callers get a clear error rather than a TypeError on None unpacking
    # (assert is stripped by -O and would silence the failure).
    if result is None:
        raise RuntimeError(
            "scheduler produced an infeasible order after greedy+2-opt; "
            "check that travel_min is deterministic"
        )

    stops, return_travel = result
    return Itinerary(
        day=Day(date=trip.day, stops=tuple(stops), return_travel_min=return_travel),
        unscheduled=tuple(unscheduled),
    )
