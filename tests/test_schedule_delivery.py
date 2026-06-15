"""Integration tests for the M1 delivery surfaces: build_schedule, CLI, and POST /schedule.

These exercise the full path from request to formatted itinerary so that the
application layer (build_schedule.py, cli.py, web/routes/schedule.py) stays
covered as new code is added on top.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_FIXTURE = Path(__file__).parent / "fixtures" / "oneday.json"


def _fixture_data() -> Any:
    return json.loads(_FIXTURE.read_text())


# ---------------------------------------------------------------------------
# build_schedule use-case
# ---------------------------------------------------------------------------


def test_build_schedule_returns_itinerary() -> None:
    from datetime import date

    from tripplanner.application.build_schedule import build_schedule
    from tripplanner.domain.models import Coord, Lodging, Place, RankedPlace, Trip

    def _hhmm(s: str) -> int:
        h, m = s.split(":")
        return int(h) * 60 + int(m)

    data = _fixture_data()
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
    assert len(itin.day.stops) > 0


# ---------------------------------------------------------------------------
# CLI — schedule command
# ---------------------------------------------------------------------------


def test_cli_schedule_prints_itinerary(capsys: pytest.CaptureFixture[str]) -> None:
    from tripplanner import cli

    cli.main(["schedule", str(_FIXTURE)])
    out = capsys.readouterr().out
    assert "Lisbon" in out or "09:" in out  # date header or first departure time
    assert "Total travel:" in out


def test_cli_no_subcommand_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    from tripplanner import cli

    cli.main([])
    out = capsys.readouterr().out
    assert "schedule" in out


# ---------------------------------------------------------------------------
# POST /schedule endpoint
# ---------------------------------------------------------------------------


def test_post_schedule_returns_201_with_itinerary() -> None:
    from tripplanner.web.app import app

    data = _fixture_data()
    resp = TestClient(app).post("/schedule", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["feasible"] is True
    assert "Total travel:" in body["day_view"]
    assert isinstance(body["unscheduled"], list)


def test_post_schedule_unfeasible_trip_returns_201_with_unscheduled() -> None:
    """A trip whose only place is closed all day is returned feasible=False."""
    from tripplanner.web.app import app

    data = _fixture_data()
    # Close every place before the day starts so none can be scheduled
    for p in data["places"]:
        p["opens_hhmm"] = "23:00"
        p["closes_hhmm"] = "23:30"
    resp = TestClient(app).post("/schedule", json=data)
    assert resp.status_code == 201
    assert resp.json()["feasible"] is False
    assert len(resp.json()["unscheduled"]) == len(data["places"])
