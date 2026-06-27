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
    resp = _CLIENT.post("/schedule", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["feasible"] is True
    assert "Day 1" in data["day_view"]
    assert "Day 2" in data["day_view"]
    assert data["unscheduled"] == []


def test_multiday_endpoint_rejects_malformed_body() -> None:
    # Missing required fields → Pydantic 422, not a 500.
    resp = _CLIENT.post("/schedule", json={"city": "Lisbon"})
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


def _shut(pid: str, lat: float, lng: float) -> dict[str, object]:
    # Hours that no normal day window can satisfy → the place can never be scheduled.
    return {**_place(pid, lat, lng), "opens_hhmm": "23:00", "closes_hhmm": "23:30"}


def test_overcommitted_schedule_returns_409_pushback() -> None:
    body = {
        "city": "Tokyo",
        "start_date": "2026-07-01",
        "lodging_name": "Hotel",
        "lodging_lat": 35.67,
        "lodging_lng": 139.73,
        "day_start_hhmm": "09:00",
        "day_end_hhmm": "18:00",
        "places": [_shut("A", 35.66, 139.70), _shut("B", 35.67, 139.71)],
    }
    resp = _CLIENT.post("/schedule", json=body)
    assert resp.status_code == 409, resp.text
    data = resp.json()
    assert data["feasible"] is False
    assert data["over_by"] == data["requested"] - data["fits"] > 0
    assert data["suggestions"], "the 409 body must carry a way forward"


def test_rating_field_is_accepted_on_places() -> None:
    body = {
        "city": "Tokyo",
        "start_date": "2026-07-01",
        "lodging_name": "Hotel",
        "lodging_lat": 35.67,
        "lodging_lng": 139.73,
        "day_start_hhmm": "09:00",
        "day_end_hhmm": "18:00",
        "places": [
            {**_place("A", 35.66, 139.70), "rating": 5},
            {**_place("B", 35.67, 139.71), "rating": 1},
        ],
    }
    resp = _CLIENT.post("/schedule", json=body)
    assert resp.status_code == 201, resp.text
