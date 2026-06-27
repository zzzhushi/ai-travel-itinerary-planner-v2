"""Schedule route: POST /schedule."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tripplanner.application.build_schedule import build_schedule
from tripplanner.application.presenters import format_itinerary
from tripplanner.domain.feasibility import check_feasibility
from tripplanner.domain.models import (
    Coord,
    Lodging,
    MealWindow,
    Place,
    RankedPlace,
    Trip,
)
from tripplanner.services.travel import haversine_minutes

router = APIRouter()


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------------------
# Pydantic schemas (HTTP layer — JSON in/out; distinct from domain dataclasses)
# ---------------------------------------------------------------------------
# These sit at the HTTP boundary: they validate incoming JSON and shape the
# response. Domain dataclasses (Trip, Itinerary, etc.) know nothing about HTTP;
# these models know nothing about routing logic. The `to_ranked()` method on
# PlaceIn is the only bridge between the two layers.


class PlaceIn(BaseModel):
    """One candidate place submitted by the caller."""

    id: str
    name: str
    category: str
    lat: float
    lng: float
    opens_hhmm: str
    closes_hhmm: str
    duration_min: int | None = None
    rating: int = 3  # 1-5; influences which places survive a capacity trim

    def to_ranked(self) -> RankedPlace:
        return RankedPlace(
            place=Place(
                id=self.id,
                name=self.name,
                category=self.category,
                coord=Coord(lat=self.lat, lng=self.lng),
                opens_min=_hhmm(self.opens_hhmm),
                closes_min=_hhmm(self.closes_hhmm),
            ),
            rating=self.rating,
            duration_override_min=self.duration_min,
        )


class MealWindowIn(BaseModel):
    """A named eating slot the scheduler should fill with a restaurant visit."""

    name: str
    earliest_hhmm: str
    latest_hhmm: str
    duration_min: int


class TripRequest(BaseModel):
    """Request body for POST /schedule. num_days=1 (default) is a single-day trip."""

    city: str
    start_date: str  # ISO date "YYYY-MM-DD"
    num_days: int = 1
    lodging_name: str
    lodging_lat: float
    lodging_lng: float
    arrival_hhmm: str | None = None
    departure_hhmm: str | None = None
    day_start_hhmm: str
    day_end_hhmm: str
    places: list[PlaceIn]
    walking_tolerance: float = 1.0
    walking_neighborhood_min: int = 30
    plan_meals: bool = False
    meal_windows: list[MealWindowIn] = []


class ScheduleResponse(BaseModel):
    """Response body for POST /schedule."""

    feasible: bool
    day_view: str
    unscheduled: list[str]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/schedule", status_code=201, response_model=None)
async def post_schedule(body: TripRequest) -> ScheduleResponse | JSONResponse:
    trip = Trip(
        city=body.city,
        start_date=date.fromisoformat(body.start_date),
        lodging=Lodging(
            name=body.lodging_name,
            coord=Coord(lat=body.lodging_lat, lng=body.lodging_lng),
        ),
        day_start_min=_hhmm(body.day_start_hhmm),
        day_end_min=_hhmm(body.day_end_hhmm),
        places=tuple(p.to_ranked() for p in body.places),
        num_days=body.num_days,
        arrival_min=_hhmm(body.arrival_hhmm) if body.arrival_hhmm else None,
        departure_min=_hhmm(body.departure_hhmm) if body.departure_hhmm else None,
        walking_neighborhood_min=body.walking_neighborhood_min,
        walking_tolerance=body.walking_tolerance,
        plan_meals=body.plan_meals,
        meal_windows=tuple(
            MealWindow(
                name=mw.name,
                earliest_min=_hhmm(mw.earliest_hhmm),
                latest_min=_hhmm(mw.latest_hhmm),
                duration_min=mw.duration_min,
            )
            for mw in body.meal_windows
        ),
    )
    # Feasibility gate: an over-committed, anchor-conflicting, or closed-on-all-days
    # request is a first-class 409 pushback (with the numbers), not a built schedule.
    report = check_feasibility(trip, haversine_minutes)
    if not report.feasible:
        return JSONResponse(
            status_code=409,
            content={
                "feasible": False,
                "requested": report.requested,
                "fits": report.fits,
                "over_by": report.over_by,
                "anchor_conflicts": list(report.anchor_conflicts),
                "closed_all_days": list(report.closed_all_days),
                "suggestions": list(report.suggestions),
            },
        )

    itin = build_schedule(trip)
    return ScheduleResponse(
        feasible=itin.is_feasible,
        day_view=format_itinerary(itin),
        unscheduled=[rp.place.name for rp in itin.unscheduled],
    )
