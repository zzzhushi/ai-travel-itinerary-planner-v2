"""Observability tests beyond the M0 smoke contract: the error path, the
walking-skeleton use-case's tracing, and the file sink (the no-stream path).
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from tripplanner.application.skeleton import walking_skeleton
from tripplanner.observability import Component, configure_observability, span


def _last_log(buf: io.StringIO) -> dict[str, Any]:
    lines: list[dict[str, Any]] = [
        json.loads(line) for line in buf.getvalue().splitlines() if line.strip()
    ]
    assert lines, "no log lines were emitted"
    return lines[-1]


def test_walking_skeleton_emits_traced_log() -> None:
    buf = io.StringIO()
    configure_observability(stream=buf)
    result = walking_skeleton()
    assert result["status"] == "ok"
    log = _last_log(buf)
    assert log["operation"] == "skeleton.healthcheck"
    assert log["component"] == "web"
    assert log["outcome"] == "ok"
    assert len(log["trace_id"]) == 32  # real OTel trace id, not a stub


def test_span_error_path_logs_and_reraises() -> None:
    buf = io.StringIO()
    configure_observability(stream=buf)
    with pytest.raises(ValueError, match="boom"), span("thing.do", component=Component.DOMAIN):
        raise ValueError("boom")
    log = _last_log(buf)
    assert log["outcome"] == "error"
    assert log["error.type"] == "ValueError"
    assert "boom" in log["error.message"]


def test_file_sink_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "app.jsonl"
    monkeypatch.setenv("TRIPPLANNER_LOG_FILE", str(log_path))
    configure_observability()  # stream=None -> stdout + file sink
    with span("thing.do", component=Component.DOMAIN):
        pass
    assert log_path.exists()
    last = json.loads(log_path.read_text().splitlines()[-1])
    assert last["operation"] == "thing.do"
    assert last["outcome"] == "ok"
