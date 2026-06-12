#!/usr/bin/env python3
"""PostToolUse hook: auto-fix lint and format on any edited Python file.

Convenience, not a gate — always exits 0. The Stop hook and task loop are
the gates. Inert until the project is scaffolded (no pyproject.toml).
"""
import json
import os
import shutil
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    file_path = (data.get("tool_input") or {}).get("file_path", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not file_path.endswith(".py") or not os.path.isfile(file_path):
        return
    if not os.path.isfile(os.path.join(project_dir, "pyproject.toml")):
        return
    # hook scripts and skill scripts lint under their own rules; skip them
    if f"{os.sep}.claude{os.sep}" in file_path:
        return

    runner = ["uv", "run", "ruff"] if shutil.which("uv") else ["ruff"]
    if runner[0] == "ruff" and not shutil.which("ruff"):
        return
    for args in (["check", "--fix", "--quiet"], ["format", "--quiet"]):
        subprocess.run(runner + args + [file_path], cwd=project_dir,
                       capture_output=True, timeout=60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a broken lint hook must never block editing
    sys.exit(0)
