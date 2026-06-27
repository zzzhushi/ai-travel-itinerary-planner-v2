"""Command-line entry point. Thin: parse args, delegate to application use-cases."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from tripplanner import __version__
from tripplanner.application.build_schedule import build_schedule
from tripplanner.application.presenters import format_itinerary
from tripplanner.domain.models import (
    Coord,
    Lodging,
    MealWindow,
    Place,
    RankedPlace,
    Trip,
)


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _parse_place(p: dict[str, Any]) -> RankedPlace:
    return RankedPlace(
        place=Place(
            id=p["id"],
            name=p["name"],
            category=p["category"],
            coord=Coord(lat=p["lat"], lng=p["lng"]),
            opens_min=_hhmm(p["opens_hhmm"]),
            closes_min=_hhmm(p["closes_hhmm"]),
        ),
        rating=p.get("rating", 3),
        duration_override_min=p.get("duration_min"),
    )


def _lodging(data: dict[str, Any]) -> Lodging:
    return Lodging(
        name=data["lodging_name"],
        coord=Coord(lat=data["lodging_lat"], lng=data["lodging_lng"]),
    )


def _cmd_schedule(fixture_path: str) -> None:
    data = json.loads(Path(fixture_path).read_text())
    meal_windows = tuple(
        MealWindow(
            name=mw["name"],
            earliest_min=_hhmm(mw["earliest_hhmm"]),
            latest_min=_hhmm(mw["latest_hhmm"]),
            duration_min=mw["duration_min"],
        )
        for mw in data.get("meal_windows", [])
    )
    trip = Trip(
        city=data["city"],
        start_date=date.fromisoformat(data["start_date"]),
        lodging=_lodging(data),
        day_start_min=_hhmm(data["day_start_hhmm"]),
        day_end_min=_hhmm(data["day_end_hhmm"]),
        places=tuple(_parse_place(p) for p in data["places"]),
        num_days=data.get("num_days", 1),
        arrival_min=_hhmm(data["arrival_hhmm"]) if "arrival_hhmm" in data else None,
        departure_min=_hhmm(data["departure_hhmm"]) if "departure_hhmm" in data else None,
        walking_tolerance=data.get("walking_tolerance", 1.0),
        plan_meals=data.get("plan_meals", False),
        meal_windows=meal_windows,
    )
    print(format_itinerary(build_schedule(trip)))


def _cmd_rate(fixture_path: str, place_id: str, rating: int, duration: int | None) -> None:
    """Capture a 1-5 rating (and optional duration override) for one place by
    writing it back into the fixture, so a later `schedule` run picks it up. This
    is the fixture-based stand-in for the persisted PUT /ratings operation."""
    if not 1 <= rating <= 5:
        raise SystemExit(f"rating must be 1-5, got {rating}")
    path = Path(fixture_path)
    data = json.loads(path.read_text())
    for place in data["places"]:
        if place["id"] == place_id:
            place["rating"] = rating
            if duration is not None:
                place["duration_min"] = duration
            path.write_text(json.dumps(data, indent=2) + "\n")
            print(f"Rated {place_id}: {rating}/5" + (f", {duration} min" if duration else ""))
            return
    raise SystemExit(f"place '{place_id}' not found in {fixture_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tripplanner", description="AI travel itinerary planner")
    parser.add_argument("--version", action="version", version=f"tripplanner {__version__}")
    sub = parser.add_subparsers(dest="command")
    sched = sub.add_parser(
        "schedule", help="Route a trip (single- or multi-day) from a JSON fixture"
    )
    sched.add_argument("fixture", help="path to trip JSON file")

    rate = sub.add_parser("rate", help="Set a 1-5 rating (and optional duration) for a place")
    rate.add_argument("fixture", help="path to trip JSON file")
    rate.add_argument("--place", required=True, help="place id to rate")
    rate.add_argument("--rating", type=int, required=True, help="rating 1-5")
    rate.add_argument("--duration", type=int, help="optional duration override in minutes")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "schedule":
        _cmd_schedule(args.fixture)
    elif args.command == "rate":
        _cmd_rate(args.fixture, args.place, args.rating, args.duration)
    else:
        parser.print_help()
