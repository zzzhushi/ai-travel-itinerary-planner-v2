"""Single-day routing: order stops to minimize travel within all constraints.

Pure domain. Travel time is an injected callable (haversine lives in services/,
and domain imports nothing from services).

Algorithm: greedy nearest-feasible insertion to get an initial ordering,
then 2-opt local search to reduce total travel without violating time windows.

Fixed-time anchors (dinner reservations, timed entries) are placed at their
exact times; the day is sliced into segments between consecutive anchors and
flexible places are greedily fitted into each segment (see `_schedule_with_anchors`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import pairwise

from tripplanner.domain.durations import resolve_duration_min
from tripplanner.domain.models import (
    Coord,
    Day,
    FixedAnchor,
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


def _greedy_segment(
    candidates: list[RankedPlace],
    start_coord: Coord,
    start_time: int,
    end_coord: Coord,
    end_deadline: int,
    travel_min: TravelMinutes,
) -> tuple[list[RankedPlace], list[RankedPlace]]:
    """Greedily fit flexible places into one time segment that begins at
    (start_coord, start_time) and must arrive at end_coord no later than
    end_deadline. At each step pick the earliest-finishing reachable place that
    still leaves time to reach end_coord by the deadline. Returns
    (scheduled_order, unscheduled).

    The whole-day flexible schedule is the special case end_coord == lodging,
    end_deadline == day_end; anchor segments reuse this with the next anchor's
    location and arrival time as the deadline."""
    remaining = list(candidates)
    ordered: list[RankedPlace] = []
    current_time = start_time
    current_coord = start_coord

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
            if depart + travel_min(place.coord, end_coord) > end_deadline:
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


def _greedy(
    candidates: list[RankedPlace],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> tuple[list[RankedPlace], list[RankedPlace]]:
    """Whole-day greedy: the anchorless special case of `_greedy_segment` where
    the route starts and ends at lodging within the day window."""
    return _greedy_segment(candidates, lodging, day_start, lodging, day_end, travel_min)


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
    returned in `Itinerary.unscheduled` (never silently dropped).

    Fixed-time anchors, if any, are seated at their exact times and flexible
    places routed around them via segment slicing."""
    lodging = trip.lodging.coord

    if trip.anchors:
        stops, return_travel, unscheduled = _schedule_with_anchors(
            list(trip.places),
            trip.anchors,
            lodging,
            trip.day_start_min,
            trip.day_end_min,
            travel_min,
        )
        return Itinerary(
            days=(Day(date=trip.start_date, stops=tuple(stops), return_travel_min=return_travel),),
            unscheduled=tuple(unscheduled),
        )

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
        days=(Day(date=trip.start_date, stops=tuple(stops), return_travel_min=return_travel),),
        unscheduled=tuple(unscheduled),
    )


def _schedule_with_anchors(
    places: list[RankedPlace],
    anchors: Sequence[FixedAnchor],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> tuple[list[ScheduledStop], int, list[RankedPlace]]:
    """Seat each anchor at its exact time and greedily fill the segments between
    them with flexible places. Anchors are sorted by arrival; the day is cut into
    segments [previous fixed point -> next anchor] and a final [last anchor ->
    lodging] leg, each filled by `_greedy_segment` so flexible stops never push an
    anchor off its time. Returns (stops, return_travel_min, unscheduled).

    Anchors are always seated, even if the chain is physically impossible — that
    conflict is reported separately by `detect_anchor_conflicts` (a 409 pushback
    is a first-class outcome, not a scheduling crash)."""
    ordered_anchors = sorted(anchors, key=lambda a: a.arrival_min)
    remaining = list(places)
    stops: list[ScheduledStop] = []
    current_time = day_start
    current_coord = lodging

    for anchor in ordered_anchors:
        seg, remaining = _greedy_segment(
            remaining,
            current_coord,
            current_time,
            anchor.place.coord,
            anchor.arrival_min,
            travel_min,
        )
        for rp in seg:
            travel = travel_min(current_coord, rp.place.coord)
            arrive = max(current_time + travel, rp.place.opens_min)
            depart = arrive + resolve_duration_min(rp)
            stops.append(ScheduledStop(rp.place, arrive, depart, travel))
            current_time, current_coord = depart, rp.place.coord

        travel_to_anchor = travel_min(current_coord, anchor.place.coord)
        stops.append(
            ScheduledStop(
                place=anchor.place,
                arrive_min=anchor.arrival_min,
                depart_min=anchor.arrival_min + anchor.duration_min,
                travel_from_prev_min=travel_to_anchor,
            )
        )
        current_time = anchor.arrival_min + anchor.duration_min
        current_coord = anchor.place.coord

    seg, remaining = _greedy_segment(
        remaining, current_coord, current_time, lodging, day_end, travel_min
    )
    for rp in seg:
        travel = travel_min(current_coord, rp.place.coord)
        arrive = max(current_time + travel, rp.place.opens_min)
        depart = arrive + resolve_duration_min(rp)
        stops.append(ScheduledStop(rp.place, arrive, depart, travel))
        current_time, current_coord = depart, rp.place.coord

    return_travel = travel_min(current_coord, lodging)
    return stops, return_travel, remaining


def detect_anchor_conflicts(
    anchors: Sequence[FixedAnchor],
    lodging: Coord,
    day_start: int,
    day_end: int,
    travel_min: TravelMinutes,
) -> list[str]:
    """Return human-readable reasons the anchor set cannot be honored, empty if it
    can. Checks each anchor sits inside the day window and its own opening hours,
    that the first is reachable from lodging in time, and that every consecutive
    pair leaves enough travel time. Used by the feasibility pre-check before
    building (a mutually-impossible anchor pair is a 409, not a silent drop)."""
    conflicts: list[str] = []
    ordered = sorted(anchors, key=lambda a: a.arrival_min)

    for a in ordered:
        end = a.arrival_min + a.duration_min
        if a.arrival_min < day_start or end > day_end:
            conflicts.append(f"anchor '{a.place.id}' falls outside the day window")
        if a.arrival_min < a.place.opens_min or end > a.place.closes_min:
            conflicts.append(f"anchor '{a.place.id}' falls outside its opening hours")

    if ordered:
        first = ordered[0]
        if day_start + travel_min(lodging, first.place.coord) > first.arrival_min:
            conflicts.append(f"anchor '{first.place.id}' is unreachable from lodging by its time")

    for prev, nxt in pairwise(ordered):
        available = nxt.arrival_min - (prev.arrival_min + prev.duration_min)
        needed = travel_min(prev.place.coord, nxt.place.coord)
        if available < needed:
            conflicts.append(
                f"cannot travel from anchor '{prev.place.id}' to '{nxt.place.id}' in time "
                f"({needed} min needed, {available} min available)"
            )

    return conflicts
