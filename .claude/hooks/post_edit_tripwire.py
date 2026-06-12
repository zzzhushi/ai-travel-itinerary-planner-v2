#!/usr/bin/env python3
"""PostToolUse hook: flag newly added checker-suppressions in Python files.

The three classic corner-cutting moves are suppressing the linter, suppressing
the type checker, and skipping the failing test. Exit 2 feeds a warning back
to Claude (it does not undo the edit); guardrails require an adjacent
justification comment for every suppression.
"""
import json
import sys

PATTERNS = (
    "# noqa",
    "# type: ignore",
    "pytest.mark.skip",
    "@skip",
    "unittest.skip",
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py") or "/.claude/" in file_path:
        return 0

    # Edit: only patterns ADDED (in new_string, not old_string). Write: whole content.
    new_text = tool_input.get("new_string") or tool_input.get("content") or ""
    old_text = tool_input.get("old_string") or ""
    added = [p for p in PATTERNS if p in new_text and old_text.count(p) < new_text.count(p)]
    if not added:
        return 0

    print(
        f"Tripwire: this edit to {file_path} adds suppression(s): {', '.join(added)}. "
        "Guardrails require an adjacent comment justifying each suppression — "
        "prefer fixing the underlying finding. If already justified, proceed.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
