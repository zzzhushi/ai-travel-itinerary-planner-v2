#!/usr/bin/env python3
"""Run a mechanical coding task on a local model via Ollama.

Opens a tool-calling loop so the model can read project files lazily via the
read_file tool, then writes only whitelisted paths once the model emits
===FILE=== blocks. Appends an experiment record to .local-llm-log.jsonl.
Review of the resulting diff is the CALLER's job — this script never commits.

Usage:
  local_task.py --brief brief.md --allow src/foo.py --allow tests/test_foo.py
                [--model qwen3.6:latest] [--repair-log pytest_output.txt]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = os.environ.get("TRIPPLANNER_LOCAL_MODEL", "qwen3.6:latest")

OLLAMA_URL = "http://localhost:11434/api/chat"
LOG_PATH = Path(".local-llm-log.jsonl")

_MAX_TOOL_ROUNDS = 20  # guard against runaway read loops

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

SYSTEM_PROMPT = """You are implementing one small, fully-specified coding task.
You have a read_file tool — call it for any file you need to inspect before editing.
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


def call_ollama(model: str, brief: str, timeout: int = 600) -> str:
    """Run the Ollama tool-calling loop. Executes read_file calls as they arrive;
    returns the final text response containing ===FILE=== blocks."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": brief},
    ]
    for _ in range(_MAX_TOOL_ROUNDS):
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 32768},
        }
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True, help="markdown brief file")
    ap.add_argument("--allow", action="append", required=True, help="writable path (repeatable)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--repair-log", help="prior verify output to append (repair round)")
    args = ap.parse_args()

    brief = Path(args.brief).read_text()
    if args.repair_log:
        brief += "\n\n## Previous attempt failed verification:\n" + Path(args.repair_log).read_text()
    brief += "\n\n## Allowed files (write ONLY these):\n" + "\n".join(f"- {p}" for p in args.allow)

    # Initial brief token estimate; each read_file response grows the context further.
    est_tokens = len(brief) // 4
    if est_tokens > 32_000:
        sys.exit(f"Brief ~{est_tokens} tokens, exceeds 32k curation budget. Trim it.")

    output = call_ollama(args.model, brief)
    files = extract_files(output)
    if not files:
        sys.exit("Model produced no ===FILE=== blocks. Raw output:\n" + output[:2000])

    allowed = {str(Path(p)) for p in args.allow}
    written, refused = [], []
    for path, content in files.items():
        norm = str(Path(path))
        if norm in allowed and ".." not in Path(norm).parts:
            Path(norm).parent.mkdir(parents=True, exist_ok=True)
            Path(norm).write_text(content if content.endswith("\n") else content + "\n")
            written.append(norm)
        else:
            refused.append(norm)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "brief_tokens_est": est_tokens,
        "repair_round": bool(args.repair_log),
        "written": written,
        "refused": refused,
        # caller appends after review: {"review_findings": N, "accepted": bool}
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Wrote {written}; refused {refused or 'none'}. Now verify (ruff/mypy/pytest) and review the diff.")


if __name__ == "__main__":
    main()
