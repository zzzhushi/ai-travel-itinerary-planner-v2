#!/usr/bin/env python3
"""PreToolUse hook for Bash: audit log + main-branch commit guard.

1. Appends every command to .claude/audit.log (local, gitignored) — a
   deterministic record of what was actually run, independent of transcripts.
2. Blocks `git commit` while on the default branch (main/master): commits
   belong on milestone/feature branches per CLAUDE.md conventions.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# `git ... commit` within one command segment (no |&; separator between them),
# so `git -C path commit` is caught. Biased toward over-matching: a false block
# on main just prompts a branch; a missed commit on main is the failure we guard.
GIT_COMMIT_RE = re.compile(r"\bgit\b[^|&;\n]*\bcommit\b")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # 1. Audit log — always, one line per command, before any blocking
    try:
        log_path = os.path.join(project_dir, ".claude", "audit.log")
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(log_path, "a") as f:
            f.write(f"{ts} {command!r}\n")
    except OSError:
        pass  # auditing must never break command execution

    # 2. Main-branch commit guard
    if GIT_COMMIT_RE.search(command):
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_dir, capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            return 0
        if branch in ("main", "master"):
            print(
                f"Blocked: you are on '{branch}'. Commits go on milestone/feature "
                "branches (CLAUDE.md conventions) — create a branch first.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
