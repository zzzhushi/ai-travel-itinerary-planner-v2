# Local-LLM routing (default executor for non-complex tasks; instrumented)

## Hypothesis under test

That mechanical- and standard-rated tasks can be implemented by a local model (free, private) without the review-and-repair cost eating the savings. Still **instrumented** — every run logs data so the economics stay decidable; if the data turns (decision rule below), fall back to cloud.

## Qualification (all must hold)

- A **committed failing test** already pins the behavior — this is the primary gate. Without it there is no mechanical way to verify local output before review.
- Touched files total < ~500 lines and the curated brief fits in ≤32k tokens (local model quality degrades past that regardless of advertised context).
- No security surface, no concurrency, no new dependencies.
- Task rated `mechanical` or `standard` by default. **Complex tasks are eligible** if the brief can be curated fully — complexity raises the brief-curation cost, but is not a hard ban. M2 eval confirmed complex algorithmic tasks (k-means, constraint-slotting) pass when committed tests are strong and the full file is in the brief.

Fails any check → run the task normally on the cloud model and say so.

## Process

1. **Curate the brief** (this is where the engineering lives — the local model gets conclusions, not exploration ability): task description; **full text of every file to be modified** (no `<PASTE_FILE>` placeholders, no excerpts — a placeholder the model copies literally produces silent corruption); signatures/docstrings of interfaces it must call (not their bodies); the failing test verbatim; a ≤20-line excerpt of relevant conventions from `docs/engineering-standards.md`; explicit list of files it may write.
2. **Run** `scripts/local_task.py --brief <file>` — model defaults to `$TRIPPLANNER_LOCAL_MODEL` or `qwen3.6:latest`; override with `--model` (e.g. a coding-specialized `qwen3-coder` / `devstral` if pulled). Requires Ollama serving (`ollama serve`; the model loads into memory on first call). The script calls the model, extracts complete-file outputs, and writes ONLY whitelisted paths.
3. **Verify and repair:** run `uv run ruff check && uv run mypy && uv run pytest -q`. If it fails, save the output to a temp file and re-run with `--repair-log <output_file>` — the script appends the errors to the brief automatically. Up to 2 repair rounds; after 2, discard and implement on the cloud model.
4. **Top-model review (you, now):** read the full diff against the brief and guardrails — convention violations, hardcoding, edge cases. Fix or reject. **Never commit unreviewed local-model output.**
5. **Log the data point** — the script appends to `.local-llm-log.jsonl`: model, brief token estimate, repair rounds, review findings count, accepted/rejected. `/retro` reads this log to call the experiment.

## Decision rule for the experiment

After ~10 logged runs: if median review-findings ≥ 2 or rejection rate ≥ 30%, the hypothesis failed for this model/task mix — retire the flag (with an ADR in docs/decisions/ recording the data) rather than letting a degraded path linger.
