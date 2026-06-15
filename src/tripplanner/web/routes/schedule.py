"""POST /schedule — build a single-day and multi day itinerary from a JSON trip description."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from tripplanner.application.build_schedule import build_multiday_schedule, build_schedule
from tripplanner.application.presenters import format_day, format_multiday
from tripplanner.domain.models import (
    Coord,
    Lodging,
    MealWindow,
    MultiDayTrip,
    Place,
    RankedPlace,
    Trip,
)

router = APIRouter()


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


class PlaceIn(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lng: float
    opens_hhmm: str
    closes_hhmm: str
    duration_min: int | None = None

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
            duration_override_min=self.duration_min,
        )


class TripRequest(BaseModel):
    city: str
    day: str  # ISO date "YYYY-MM-DD"
    lodging_name: str
    lodging_lat: float
    lodging_lng: float
    day_start_hhmm: str
    day_end_hhmm: str
    places: list[PlaceIn]


class ScheduleResponse(BaseModel):
    feasible: bool
    day_view: str
    unscheduled: list[str]


@router.post("/schedule", status_code=201)
async def post_schedule(body: TripRequest) -> ScheduleResponse:
    trip = Trip(
        city=body.city,
        day=date.fromisoformat(body.day),
        lodging=Lodging(
            name=body.lodging_name,
            coord=Coord(lat=body.lodging_lat, lng=body.lodging_lng),
        ),
        day_start_min=_hhmm(body.day_start_hhmm),
        day_end_min=_hhmm(body.day_end_hhmm),
        places=tuple(p.to_ranked() for p in body.places),
    )
    itin = build_schedule(trip)
    return ScheduleResponse(
        feasible=itin.is_feasible,
        day_view=format_day(itin),
        unscheduled=[rp.place.name for rp in itin.unscheduled],
    )


class MealWindowIn(BaseModel):
    name: str
    earliest_hhmm: str
    latest_hhmm: str
    duration_min: int


class MultiDayTripRequest(BaseModel):
    city: str
    start_date: str  # ISO date "YYYY-MM-DD"
    num_days: int
    lodging_name: str
    lodging_lat: float
    lodging_lng: float
    arrival_hhmm: str
    departure_hhmm: str
    day_start_hhmm: str
    day_end_hhmm: str
    places: list[PlaceIn]
    walking_tolerance: float = 1.0
    plan_meals: bool = False
    meal_windows: list[MealWindowIn] = []


@router.post("/schedule/multiday", status_code=201)
async def post_schedule_multiday(body: MultiDayTripRequest) -> ScheduleResponse:
    trip = MultiDayTrip(
        city=body.city,
        start_date=date.fromisoformat(body.start_date),
        num_days=body.num_days,
        lodging=Lodging(
            name=body.lodging_name,
            coord=Coord(lat=body.lodging_lat, lng=body.lodging_lng),
        ),
        arrival_min=_hhmm(body.arrival_hhmm),
        departure_min=_hhmm(body.departure_hhmm),
        day_start_min=_hhmm(body.day_start_hhmm),
        day_end_min=_hhmm(body.day_end_hhmm),
        places=tuple(p.to_ranked() for p in body.places),
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
    itin = build_multiday_schedule(trip)
    return ScheduleResponse(
        feasible=itin.is_feasible,
        day_view=format_multiday(itin),
        unscheduled=[rp.place.name for rp in itin.unscheduled],
    )
