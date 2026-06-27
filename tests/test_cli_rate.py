"""Tests for the CLI `rate` command (M3 rating capture into the fixture)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tripplanner.cli import main


def _fixture(tmp_path: Path) -> Path:
    data = {
        "city": "C",
        "start_date": "2026-07-01",
        "lodging_name": "H",
        "lodging_lat": 0.0,
        "lodging_lng": 0.0,
        "day_start_hhmm": "09:00",
        "day_end_hhmm": "20:00",
        "places": [
            {
                "id": "A",
                "name": "A",
                "category": "sight",
                "lat": 1.0,
                "lng": 0.0,
                "opens_hhmm": "09:00",
                "closes_hhmm": "20:00",
            }
        ],
    }
    p = tmp_path / "trip.json"
    p.write_text(json.dumps(data))
    return p


def test_rate_writes_rating_and_duration_into_fixture(tmp_path: Path) -> None:
    p = _fixture(tmp_path)
    main(["rate", str(p), "--place", "A", "--rating", "5", "--duration", "90"])
    place = json.loads(p.read_text())["places"][0]
    assert place["rating"] == 5
    assert place["duration_min"] == 90


def test_rate_then_schedule_picks_up_the_rating(tmp_path: Path) -> None:
    # The fixture round-trips: rate, then schedule reads the updated rating.
    p = _fixture(tmp_path)
    main(["rate", str(p), "--place", "A", "--rating", "4"])
    main(["schedule", str(p)])  # must not raise — the rated fixture is valid input


def test_rate_rejects_out_of_range_rating(tmp_path: Path) -> None:
    p = _fixture(tmp_path)
    with pytest.raises(SystemExit):
        main(["rate", str(p), "--place", "A", "--rating", "9"])


def test_rate_unknown_place_errors(tmp_path: Path) -> None:
    p = _fixture(tmp_path)
    with pytest.raises(SystemExit):
        main(["rate", str(p), "--place", "ZZZ", "--rating", "3"])
