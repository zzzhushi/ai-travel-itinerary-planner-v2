"""Feasibility pre-check: decide whether a trip can be built before building it.

Returns a structured FeasibilityReport so the CLI and web layers can surface a
409-style pushback (numbers + swap offers) instead of silently dropping places.
A first-class outcome, not an error — see docs/api-contract.md.

Three ways a trip can be infeasible, each reported independently:
- over-commitment — more requested places than fit the available days;
- mutually infeasible anchors — fixed-time events that can't all be honored;
- closed-on-all-days — a place open on none of the trip's weekdays.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import timedelta

from tripplanner.domain.models import Coord, Trip
from tripplanner.domain.planner import schedule_trip
from tripplanner.domain.pushback import render_suggestions
from tripplanner.domain.scheduler import detect_anchor_conflicts

TravelMinutes = Callable[[Coord, Coord], int]


@dataclass(frozen=True)
class FeasibilityReport:
    """The verdict of `check_feasibility`. `feasible` is the headline; the rest
    are the numbers and reasons a pushback message is rendered from."""

    feasible: bool
    fits: int  # requested places that actually land in the built schedule
    requested: int  # places the user asked for
    over_by: int  # requested - fits (places that could not be scheduled)
    anchor_conflicts: tuple[str, ...]  # why fixed-time anchors can't all be honored
    closed_all_days: tuple[str, ...]  # ids of places open on no trip day
    suggestions: tuple[str, ...]  # rendered swap/drop offers (see pushback.py)


def _trip_weekdays(trip: Trip) -> frozenset[int]:
    """The set of weekday numbers (Mon=0..Sun=6) the trip spans."""
    return frozenset((trip.start_date + timedelta(days=d)).weekday() for d in range(trip.num_days))


def check_feasibility(trip: Trip, travel_min: TravelMinutes) -> FeasibilityReport:
    """Assess a trip without committing to a final schedule. Builds once with the
    visitable places to count how many fit, flags places closed on every trip day,
    and checks the anchor set for mutual conflicts."""
    requested = len(trip.places)

    trip_weekdays = _trip_weekdays(trip)
    closed_all_days = tuple(
        rp.place.id
        for rp in trip.places
        if rp.place.closed_weekdays and trip_weekdays <= rp.place.closed_weekdays
    )

    anchor_conflicts = tuple(
        detect_anchor_conflicts(
            trip.anchors,
            trip.lodging.coord,
            trip.day_start_min,
            trip.day_end_min,
            travel_min,
        )
    )

    # Build with only the visitable places — a place closed on every trip day can
    # never land, so excluding it keeps `fits` honest.
    closed_set = set(closed_all_days)
    visitable = tuple(rp for rp in trip.places if rp.place.id not in closed_set)
    itin = schedule_trip(replace(trip, places=visitable), travel_min)
    scheduled_ids = {s.place.id for day in itin.days for s in day.stops}
    fits = sum(1 for rp in trip.places if rp.place.id in scheduled_ids)
    # over_by is the *capacity* deficit among visitable places — closed-on-all-days
    # places are reported separately (a swap, not "drop one or add days"), so they
    # must not inflate this count.
    over_by = len(visitable) - fits

    feasible = over_by == 0 and not anchor_conflicts and not closed_all_days
    suggestions = render_suggestions(
        requested=requested,
        fits=fits,
        over_by=over_by,
        closed_all_days=closed_all_days,
        anchor_conflicts=anchor_conflicts,
    )
    return FeasibilityReport(
        feasible=feasible,
        fits=fits,
        requested=requested,
        over_by=over_by,
        anchor_conflicts=anchor_conflicts,
        closed_all_days=closed_all_days,
        suggestions=suggestions,
    )
