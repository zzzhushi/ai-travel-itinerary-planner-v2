#!/usr/bin/env python3
"""Stop hook: a turn may not end with red tests.

Runs the fast test pass; on failure, exit 2 blocks the stop and feeds the
output back so the failure gets fixed (or honestly escalated) instead of
left behind. Inert until the project is scaffolded.
"""
import json
import os
import shutil
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}
    # set when a previous stop was already blocked by this hook — never loop
    if data.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not os.path.isfile(os.path.join(project_dir, "pyproject.toml")):
        return 0
    if not os.path.isdir(os.path.join(project_dir, "tests")):
        return 0
    if not shutil.which("uv"):
        return 0

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "-q", "-x"],
            cwd=project_dir, capture_output=True, text=True, timeout=150,
        )
    except subprocess.TimeoutExpired:
        print("stop_tests hook: pytest timed out (150s); not blocking, but the suite needs attention.",
              file=sys.stderr)
        return 0

    if result.returncode in (0, 5):  # 5 = no tests collected
        return 0

    tail = "\n".join((result.stdout + result.stderr).splitlines()[-50:])
    print(f"Tests are failing — fix or explicitly escalate before stopping:\n{tail}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
