"""Web-layer tests for the schedule endpoints (M2 task 5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tripplanner.web.app import app

_CLIENT = TestClient(app)


def _place(pid: str, lat: float, lng: float, category: str = "sight") -> dict[str, object]:
    return {
        "id": pid,
        "name": pid,
        "category": category,
        "lat": lat,
        "lng": lng,
        "opens_hhmm": "09:00",
        "closes_hhmm": "20:00",
    }


def test_multiday_endpoint_returns_a_routed_plan() -> None:
    body = {
        "city": "Lisbon",
        "start_date": "2026-07-01",
        "num_days": 2,
        "lodging_name": "Hotel",
        "lodging_lat": 38.71,
        "lodging_lng": -9.14,
        "arrival_hhmm": "09:00",
        "departure_hhmm": "18:00",
        "day_start_hhmm": "09:00",
        "day_end_hhmm": "18:00",
        "places": [
            _place("A", 38.711, -9.141),
            _place("B", 38.712, -9.142),
            _place("C", 38.697, -9.206),
            _place("D", 38.698, -9.207),
        ],
    }
    resp = _CLIENT.post("/schedule/multiday", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["feasible"] is True
    assert "Day 1" in data["day_view"]
    assert "Day 2" in data["day_view"]
    assert data["unscheduled"] == []


def test_multiday_endpoint_rejects_malformed_body() -> None:
    # Missing required fields → Pydantic 422, not a 500.
    resp = _CLIENT.post("/schedule/multiday", json={"city": "Lisbon"})
    assert resp.status_code == 422


def test_walking_neighborhood_min_accepted_and_defaults() -> None:
    # walking_neighborhood_min=15 is accepted; omitting it also works (default=30).
    base = {
        "city": "Tokyo",
        "start_date": "2026-07-01",
        "lodging_name": "Hotel",
        "lodging_lat": 35.67,
        "lodging_lng": 139.73,
        "day_start_hhmm": "09:00",
        "day_end_hhmm": "18:00",
        "places": [_place("A", 35.66, 139.70), _place("B", 35.67, 139.71)],
    }
    resp_tight = _CLIENT.post("/schedule", json={**base, "walking_neighborhood_min": 15})
    assert resp_tight.status_code == 201, resp_tight.text

    resp_default = _CLIENT.post("/schedule", json=base)
    assert resp_default.status_code == 201, resp_default.text
