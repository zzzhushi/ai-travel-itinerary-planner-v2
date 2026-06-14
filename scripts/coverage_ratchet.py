#!/usr/bin/env python3
"""Coverage floor gate — fail the build if coverage drops below 70%.

The floor is intentionally permissive: CI catches catastrophic regressions
(untested modules, deleted test files) while not punishing milestones that
add new code before full test coverage is written. 50% is the absolute
minimum that would be accepted with a documented reason; below 70% is a
signal to add tests before merging.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FLOOR = 70.0
REPORT = Path("coverage.json")


def main() -> int:
    if not REPORT.exists():
        print("coverage.json not found — run pytest with --cov-report=json first", file=sys.stderr)
        return 1
    try:
        pct = round(float(json.loads(REPORT.read_text())["totals"]["percent_covered"]), 2)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"could not read coverage from {REPORT}: {exc}", file=sys.stderr)
        return 1
    if pct < FLOOR:
        print(f"FAIL: coverage {pct:.2f}% is below the {FLOOR:.0f}% floor.", file=sys.stderr)
        return 1
    print(f"OK: coverage {pct:.2f}% clears the {FLOOR:.0f}% floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
