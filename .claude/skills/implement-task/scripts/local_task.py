#!/usr/bin/env python3
"""Run a mechanical coding task on a local model via Ollama.

Reads a curated brief (markdown), asks the model for complete replacement
files, writes only whitelisted paths, and appends an experiment record to
.local-llm-log.jsonl. Review of the resulting diff is the CALLER's job —
this script never commits.

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

# The local coding model. Override per-call with --model, or globally with
# TRIPPLANNER_LOCAL_MODEL. Default is the model this project was set up with.
DEFAULT_MODEL = os.environ.get("TRIPPLANNER_LOCAL_MODEL", "qwen3.6:latest")
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
LOG_PATH = Path(".local-llm-log.jsonl")

SYSTEM_PROMPT = """You are implementing one small, fully-specified coding task.
Rules:
- Output COMPLETE replacement contents for each file you change, as:
  ===FILE: <relative/path>===
  <entire file content>
  ===END===
- Only touch files listed as allowed in the brief. No other output format.
- Make the failing test in the brief pass. Do not modify any test.
- Follow the conventions excerpt exactly. No new dependencies. No TODO stubs.
"""


def call_ollama(model: str, brief: str, timeout: int = 600) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": brief},
        ],
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
            return json.loads(resp.read())["message"]["content"]
    except urllib.error.URLError as e:
        sys.exit(f"Ollama unreachable at {OLLAMA_URL} ({e}). Is `ollama serve` running?")


def extract_files(output: str) -> dict[str, str]:
    pattern = re.compile(r"===FILE: (.+?)===\n(.*?)\n?===END===", re.DOTALL)
    return {path.strip(): content for path, content in pattern.findall(output)}


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

    # crude token estimate; the 32k curation budget is enforced here, not trusted to the model
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
