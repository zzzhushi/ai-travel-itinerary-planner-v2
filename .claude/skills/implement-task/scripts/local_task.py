#!/usr/bin/env python3
"""Run a mechanical coding task on a local model via Ollama.

Opens a tool-calling loop so the model can read project files lazily via the
read_file tool, then writes only whitelisted paths once the model emits
===FILE=== blocks. Appends an experiment record to .local-llm-log.jsonl.
Review of the resulting diff is the CALLER's job — this script never commits.

Usage:
  local_task.py --brief brief.md --allow src/foo.py --allow tests/test_foo.py
                [--model qwen3.6:latest] [--no-read]
                [--verify-cmd "uv run ruff check && uv run mypy && uv run pytest -q"]
                [--repair-log pytest_output.txt]
  local_task.py --record-review <run_ts> --findings N (--accepted | --rejected)

Pass --no-read for self-contained briefs (new pure files, fully-specified
signatures) — withholding read_file stops local models from over-exploring the
import graph and stalling out before they emit any ===FILE=== output.

--verify-cmd closes the verify/repair loop in-harness: the script runs the
command after writing files and, on failure, feeds the output back to the model
for up to 2 repair rounds — one complete log record either way. --record-review
closes the *measurement* loop: the mandatory post-run diff review is logged as
a record keyed to the run's ts, so the experiment's decision rule stays
computable (unlogged reviews were the dominant gap in M0–M3 data).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = os.environ.get("TRIPPLANNER_LOCAL_MODEL", "qwen3.6:latest")

OLLAMA_URL = "http://localhost:11434/api/chat"
LOG_PATH = Path(".local-llm-log.jsonl")

_MAX_TOOL_ROUNDS = 20  # guard against runaway read loops
_FINAL_ROUNDS = 2  # last rounds: stop offering tools and nudge, forcing ===FILE=== output
_MAX_REPAIR_ROUNDS = 2  # --verify-cmd: repair attempts before giving up (cloud takes over)
_VERIFY_TAIL_CHARS = 3000  # how much verify output to feed back on a repair round

# Local models sometimes walk the import graph reading files they don't need and
# never emit output. Before giving up, nudge once and stop offering the tool.
_NUDGE_MESSAGE = (
    "You have enough context. Output the ===FILE=== block(s) now and call no more tools."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the current content of a file in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from the project root, e.g. src/foo.py",
                    }
                },
                "required": ["path"],
            },
        },
    }
]

_SYSTEM_HEAD_READ = (
    "You have a read_file tool — call it for any file you need to inspect before editing."
)
_SYSTEM_HEAD_NOREAD = (
    "Everything you need is in the brief below. You have no tools — do not ask to read files."
)

SYSTEM_PROMPT_TEMPLATE = """You are implementing one small, fully-specified coding task.
{head}
When you have all the context you need, output COMPLETE replacement contents for each
file you change, as:
  ===FILE: <relative/path>===
  <entire file content>
  ===END===
- Do NOT wrap file content in markdown code fences (no ```). Raw file only.
- Only touch files listed as allowed in the brief. No other output format.
- Make the failing test pass. Do not modify any test.
- Follow the conventions excerpt exactly. No new dependencies. No TODO stubs.
"""


def _execute_read_file(path: str) -> str:
    p = Path(path)
    if ".." in p.parts:
        return "Error: path traversal not allowed"
    if not p.exists():
        return f"Error: file not found: {path}"
    return p.read_text()


def call_ollama(model: str, brief: str, timeout: int = 600, allow_read: bool = True) -> str:
    """Run the Ollama tool-calling loop. Executes read_file calls as they arrive;
    returns the final text response containing ===FILE=== blocks.

    Self-correcting tail: for the last `_FINAL_ROUNDS` the tool is withheld and a
    nudge is injected, so a model that keeps reading without emitting output is
    forced to produce ===FILE=== blocks rather than burning the loop to no effect.
    `allow_read=False` withholds the tool from the start (self-contained briefs)."""
    head = _SYSTEM_HEAD_READ if allow_read else _SYSTEM_HEAD_NOREAD
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(head=head)},
        {"role": "user", "content": brief},
    ]
    for round_idx in range(_MAX_TOOL_ROUNDS):
        # Withhold the tool for the final rounds (always, if --no-read) so the
        # model must answer with text instead of reaching for another read.
        offer_tools = allow_read and round_idx < _MAX_TOOL_ROUNDS - _FINAL_ROUNDS
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 32768},
        }
        if offer_tools:
            payload["tools"] = TOOLS
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                msg = json.loads(resp.read())["message"]
        except urllib.error.URLError as e:
            sys.exit(f"Ollama unreachable at {OLLAMA_URL} ({e}). Is `ollama serve` running?")

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return msg.get("content", "")

        # Append the assistant's tool-call turn, then each tool result.
        messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls})
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            raw_args = fn.get("arguments", {})
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            if name == "read_file":
                result = _execute_read_file(args.get("path", ""))
            else:
                result = f"Error: unknown tool {name}"
            messages.append({"role": "tool", "content": result})

        # Entering the final stretch still mid-read: nudge once before the tool
        # is withheld, so the model sees the demand for output before it answers.
        if round_idx == _MAX_TOOL_ROUNDS - _FINAL_ROUNDS - 1:
            messages.append({"role": "user", "content": _NUDGE_MESSAGE})

    sys.exit(f"Tool loop exceeded {_MAX_TOOL_ROUNDS} rounds without producing ===FILE=== output.")


def _strip_code_fence(text: str) -> str:
    """Drop a leading ```lang line and trailing ``` that local models wrap files in,
    even though the protocol says not to. Leaves fence-free content untouched."""
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].lstrip().startswith("```"):
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip() == "```":
        lines.pop()
    return "\n".join(lines)


def extract_files(output: str) -> dict[str, str]:
    """Parse ===FILE: path=== blocks. Tolerant of three drifts from the protocol:
    wrapping the body in markdown fences; ending with ``` instead of ===END===;
    and writing ===END (missing trailing ===). The block ends at the first of
    ===END===, ===END, the next ===FILE:, or end-of-output."""
    files: dict[str, str] = {}
    for block in re.split(r"===FILE:\s*", output)[1:]:  # [0] is any preamble
        header, sep, body = block.partition("===")
        if not sep:
            continue
        path = header.strip()
        for marker in ("===END===", "===END"):
            end = body.find(marker)
            if end != -1:
                body = body[:end]
                break
        if path:
            files[path] = _strip_code_fence(body)
    return files


def _write_files(files: dict[str, str], allow: list[str]) -> tuple[list[str], list[str]]:
    """Write model output to disk, restricted to the whitelist. Returns (written, refused)."""
    allowed = {str(Path(p)) for p in allow}
    written, refused = [], []
    for path, content in files.items():
        norm = str(Path(path))
        if norm in allowed and ".." not in Path(norm).parts:
            Path(norm).parent.mkdir(parents=True, exist_ok=True)
            Path(norm).write_text(content if content.endswith("\n") else content + "\n")
            written.append(norm)
        else:
            refused.append(norm)
    return written, refused


def _repair_appendix(round_num: int, verify_tail: str, files: dict[str, str]) -> str:
    """Feedback appended to the brief for a repair round: the verify failure plus the
    model's own previous files, so it fixes rather than regenerates blind (matters in
    --no-read mode, where it cannot read its previous attempt back from disk)."""
    prev = "\n".join(
        f"===FILE: {path}===\n{content}\n===END===" for path, content in files.items()
    )
    return (
        f"\n\n## Attempt {round_num} failed verification. Output (tail):\n{verify_tail}"
        f"\n\n## Your previous attempt (fix it — output corrected COMPLETE files):\n{prev}"
    )


def _record_review(args: argparse.Namespace) -> None:
    """Append the mandatory post-run review verdict, keyed to the run's ts.
    A run without a review record is an incomplete data point — /retro's decision
    rule needs findings + accepted on every run to stay computable."""
    if args.findings is None or args.accepted == args.rejected:
        sys.exit("--record-review needs --findings N and exactly one of --accepted/--rejected")
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "review_of": args.record_review,
        "review_findings": args.findings,
        "accepted": args.accepted,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Review recorded for run {args.record_review}.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", help="markdown brief file")
    ap.add_argument("--allow", action="append", help="writable path (repeatable)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--verify-cmd",
        help="verification command (e.g. the project verify line); on failure the output "
        "is fed back to the model for up to 2 in-harness repair rounds",
    )
    ap.add_argument("--repair-log", help="prior verify output to append (manual repair round)")
    ap.add_argument(
        "--no-read",
        action="store_true",
        help="withhold the read_file tool — for self-contained briefs (new pure files, "
        "fully-specified signatures) where exploration only causes the model to stall",
    )
    ap.add_argument("--record-review", metavar="RUN_TS", help="log the review verdict for a run")
    ap.add_argument("--findings", type=int, help="review findings count (with --record-review)")
    ap.add_argument("--accepted", action="store_true", help="diff accepted (with --record-review)")
    ap.add_argument("--rejected", action="store_true", help="diff rejected (with --record-review)")
    args = ap.parse_args()

    if args.record_review:
        _record_review(args)
        return
    if not args.brief or not args.allow:
        sys.exit("--brief and --allow are required (unless using --record-review)")

    brief = Path(args.brief).read_text()
    if args.repair_log:
        brief += "\n\n## Previous attempt failed verification:\n" + Path(args.repair_log).read_text()
    brief += "\n\n## Allowed files (write ONLY these):\n" + "\n".join(f"- {p}" for p in args.allow)

    # Initial brief token estimate; each read_file response grows the context further.
    est_tokens = len(brief) // 4
    if est_tokens > 32_000:
        sys.exit(f"Brief ~{est_tokens} tokens, exceeds 32k curation budget. Trim it.")

    run_ts = datetime.now(timezone.utc).isoformat()
    verify_status = "skipped"  # no --verify-cmd given
    repair_rounds = 0
    written: list[str] = []
    refused: list[str] = []

    # Initial attempt + up to _MAX_REPAIR_ROUNDS in-harness repairs (--verify-cmd only).
    for round_num in range(1 + _MAX_REPAIR_ROUNDS):
        output = call_ollama(args.model, brief, allow_read=not args.no_read)
        files = extract_files(output)
        if not files:
            sys.exit("Model produced no ===FILE=== blocks. Raw output:\n" + output[:2000])
        written, refused = _write_files(files, args.allow)

        if not args.verify_cmd:
            break
        # shell=True: the verify line is a caller-supplied compound command ("a && b");
        # this is a local dev harness, not an exposed surface.
        result = subprocess.run(args.verify_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            verify_status = "pass"
            break
        verify_status = "fail"
        if round_num < _MAX_REPAIR_ROUNDS:
            repair_rounds += 1
            tail = (result.stdout + result.stderr)[-_VERIFY_TAIL_CHARS:]
            brief += _repair_appendix(round_num, tail, files)

    record = {
        "ts": run_ts,
        "model": args.model,
        "brief_tokens_est": est_tokens,
        "repair_rounds": repair_rounds,
        "manual_repair": bool(args.repair_log),
        "no_read": args.no_read,
        "verify": verify_status,
        "written": written,
        "refused": refused,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Run ts: {run_ts}")
    print(f"Wrote {written}; refused {refused or 'none'}; verify={verify_status} "
          f"({repair_rounds} repair rounds).")
    if verify_status == "fail":
        print("Verification still failing after in-harness repairs — discard and go cloud.")
        sys.exit(1)
    print("Now review the diff, then log the verdict:")
    print(f"  local_task.py --record-review '{run_ts}' --findings N --accepted|--rejected")


if __name__ == "__main__":
    main()
