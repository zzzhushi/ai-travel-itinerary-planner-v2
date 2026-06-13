# Local-LLM routing (experimental, opt-in via --local)

## Hypothesis under test

That mechanical-rated tasks can be implemented by a local model (free, private) without the review-and-repair cost eating the savings. This is an **instrumented experiment**, not an established practice — every run logs data so the economics are decidable from evidence.

## Qualification (all must hold)

- Task rated `mechanical` at milestone-planning time (never re-rated here).
- A committed failing test already pins the behavior.
- Touched files total < ~500 lines and the curated brief fits in ≤32k tokens (local model quality degrades hard past that, regardless of advertised context).
- No security surface, no concurrency, no new dependencies.

Fails any check → run the task normally on the cloud model and say so.

## Process

1. **Curate the brief** (this is where the engineering lives — the local model gets conclusions, not exploration ability): task description; full contents of files to modify; signatures/docstrings of interfaces it must call (not their bodies); the failing test verbatim; a ≤20-line excerpt of relevant conventions from `docs/engineering-standards.md`; explicit list of files it may write.
2. **Run** `scripts/local_task.py --brief <file> --model <name>` (default `qwen3-coder:30b`; alternative `devstral`). Requires Ollama running locally (`ollama serve`). The script calls the model, extracts complete-file outputs, and writes ONLY whitelisted paths.
3. **Verify mechanically:** ruff, mypy, pytest. Up to 2 repair round-trips through the script (append the error output to the brief); after that, discard and implement on the cloud model.
4. **Top-model review (you, now):** read the full diff against the brief and guardrails — convention violations, hardcoding, edge cases. Fix or reject. **Never commit unreviewed local-model output.**
5. **Log the data point** — the script appends to `.local-llm-log.jsonl`: model, brief token estimate, repair rounds, review findings count, accepted/rejected. `/retro` reads this log to call the experiment.

## Decision rule for the experiment

After ~10 logged runs: if median review-findings ≥ 2 or rejection rate ≥ 30%, the hypothesis failed for this model/task mix — retire the flag (with an ADR in docs/decisions/ recording the data) rather than letting a degraded path linger.
