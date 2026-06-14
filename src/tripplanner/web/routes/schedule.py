"""POST /schedule — build a single-day itinerary from a JSON trip description."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from tripplanner.application.build_schedule import build_schedule
from tripplanner.application.presenters import format_day
from tripplanner.domain.models import Coord, Lodging, Place, RankedPlace, Trip

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
        places=tuple(
            RankedPlace(
                place=Place(
                    id=p.id,
                    name=p.name,
                    category=p.category,
                    coord=Coord(lat=p.lat, lng=p.lng),
                    opens_min=_hhmm(p.opens_hhmm),
                    closes_min=_hhmm(p.closes_hhmm),
                ),
                duration_override_min=p.duration_min,
            )
            for p in body.places
        ),
    )
    itin = build_schedule(trip)
    return ScheduleResponse(
        feasible=itin.is_feasible,
        day_view=format_day(itin),
        unscheduled=[rp.place.name for rp in itin.unscheduled],
    )
