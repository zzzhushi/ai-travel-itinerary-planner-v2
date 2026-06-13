#!/usr/bin/env python3
"""Coverage ratchet — fail if coverage drops below the committed baseline.

Reads `coverage.json` (produced by `pytest --cov-report=json`) and compares the
total percent covered to `.coverage-baseline`. A drop fails the build; an
improvement rewrites the baseline so the floor only ever ratchets up (commit the
updated baseline). This is the standards-doc "coverage is a ratchet, not a
target" made concrete.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASELINE = Path(".coverage-baseline")
REPORT = Path("coverage.json")
EPSILON = 0.1  # tolerate float noise


def main() -> int:
    if not REPORT.exists():
        print("coverage.json not found — run pytest with --cov-report=json first", file=sys.stderr)
        return 1
    pct = float(json.loads(REPORT.read_text())["totals"]["percent_covered"])
    baseline = float(BASELINE.read_text()) if BASELINE.exists() else 0.0
    if pct + EPSILON < baseline:
        print(f"FAIL: coverage {pct:.2f}% dropped below baseline {baseline:.2f}%", file=sys.stderr)
        return 1
    if pct > baseline:
        BASELINE.write_text(f"{pct:.2f}\n")
        print(f"Coverage baseline raised to {pct:.2f}% (was {baseline:.2f}%).")
    else:
        print(f"OK: coverage {pct:.2f}% holds the {baseline:.2f}% baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
