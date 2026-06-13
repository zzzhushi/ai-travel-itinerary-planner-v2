"""M0 exit-criteria smoke tests — the contract for the scaffolding milestone.

These prove the two delivery surfaces boot and that a log line carries the full
observability schema. They are written to fail until M0 is implemented.
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from tripplanner import __version__


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    from tripplanner import cli

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_health_endpoint() -> None:
    from tripplanner.web.app import app

    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_observability_schema() -> None:
    from tripplanner.observability import Component, configure_observability, span

    buf = io.StringIO()
    configure_observability(stream=buf)
    with span("schedule.build", component=Component.DOMAIN):
        pass

    lines = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
    assert lines, "no log lines were emitted"
    completion = lines[-1]
    for field in ("correlation_id", "trace_id", "span_id", "component", "operation", "outcome"):
        assert field in completion, f"log line missing required field: {field}"
    assert completion["operation"] == "schedule.build"
    assert completion["component"] == "domain"
    assert completion["outcome"] == "ok"
