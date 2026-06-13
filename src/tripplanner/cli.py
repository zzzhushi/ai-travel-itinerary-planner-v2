"""Command-line entry point. Thin: parse args, delegate to application use-cases.

M0 ships `--version`; M1 adds `schedule <fixture.json>`.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from tripplanner import __version__
from tripplanner.application.build_schedule import build_schedule
from tripplanner.application.presenters import format_day
from tripplanner.domain.models import Coord, Lodging, Place, RankedPlace, Trip


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tripplanner", description="AI travel itinerary planner")
    parser.add_argument("--version", action="version", version=f"tripplanner {__version__}")
    sub = parser.add_subparsers(dest="command")
    sched = sub.add_parser("schedule", help="Route a single-day trip from a JSON fixture")
    sched.add_argument("fixture", help="path to trip JSON file")
    return parser


def _cmd_schedule(fixture_path: str) -> None:
    data = json.loads(Path(fixture_path).read_text())
    trip = Trip(
        city=data["city"],
        day=date.fromisoformat(data["day"]),
        lodging=Lodging(
            name=data["lodging_name"],
            coord=Coord(lat=data["lodging_lat"], lng=data["lodging_lng"]),
        ),
        day_start_min=_hhmm(data["day_start_hhmm"]),
        day_end_min=_hhmm(data["day_end_hhmm"]),
        places=tuple(
            RankedPlace(
                place=Place(
                    id=p["id"],
                    name=p["name"],
                    category=p["category"],
                    coord=Coord(lat=p["lat"], lng=p["lng"]),
                    opens_min=_hhmm(p["opens_hhmm"]),
                    closes_min=_hhmm(p["closes_hhmm"]),
                ),
                duration_override_min=p.get("duration_min"),
            )
            for p in data["places"]
        ),
    )
    itin = build_schedule(trip)
    print(format_day(itin))


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "schedule":
        _cmd_schedule(args.fixture)
    else:
        parser.print_help()
