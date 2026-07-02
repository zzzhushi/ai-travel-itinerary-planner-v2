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

1. **Curate the brief** (this is where the engineering lives — the local model gets conclusions, not exploration ability): task description; paths of files to modify (the model calls `read_file` to fetch them — for small files, <~80 lines, pasting the full text is also fine); signatures/docstrings of interfaces it must call (not their bodies); the failing test verbatim; a ≤20-line excerpt of relevant conventions from `docs/engineering-standards.md`; explicit list of files it may write. **No `<PASTE_FILE>` placeholder tokens** — the model copies them literally; either paste the text or let the model fetch it, never a placeholder. **For self-contained tasks** — a new pure file, or fully-specified signatures with every dependency already pasted into the brief — explicitly instruct the model NOT to call `read_file`, or pass `--no-read` (below). Left to their own devices, local models walk the import graph reading files they don't need (`feasibility.py` → `pushback.py` → `__init__.py` → …) and exhaust the tool loop without emitting any output. Observed with both `qwen3.6:latest` and `qwen3-coder:30b` on un-curated M3 briefs; a brief that forbade `read_file` fixed both.
2. **Run with in-harness verification** (the normal invocation):
   ```
   .claude/skills/implement-task/scripts/local_task.py --brief <file> --allow <paths> \
       --verify-cmd "uv run ruff check && uv run mypy && uv run pytest -q"
   ```
   Model defaults to `$TRIPPLANNER_LOCAL_MODEL` or `qwen3.6:latest`; override with `--model`. Requires Ollama serving (`ollama serve`; the model loads into memory on first call). The script calls the model, extracts complete-file outputs, writes ONLY whitelisted paths, **runs the verify command itself, and on failure feeds the output (plus the model's own previous files) back for up to 2 repair rounds** — one complete log record either way; it exits non-zero if still failing (discard and implement on cloud). `--no-read` drops the `read_file` tool entirely — use it for the self-contained tasks above so the model can't stall on exploration. As a backstop even without the flag, the harness withholds the tool for the final 2 rounds and injects a "you have enough context, output now" nudge before giving up. (`--repair-log <file>` remains for a manual round when you already have verify output in hand.)
3. **Top-model review (you, now):** read the full diff against the brief and guardrails — convention violations, hardcoding, edge cases. Fix or reject. **Never commit unreviewed local-model output.**
4. **Log the review — mandatory, exact command** (the script printed the run ts):
   ```
   .claude/skills/implement-task/scripts/local_task.py --record-review '<run_ts>' --findings N --accepted|--rejected
   ```
   A run without a review record is an incomplete data point. M0–M3 evidence: 9 of 14 rows were missing review fields because this step was prose-only — the decision rule below was uncomputable. The command exists so the step is one line, not a hand-edited JSONL append.

## Decision rule for the experiment

After ~10 fully-logged runs (run + review record): if median review-findings ≥ 2 or rejection rate ≥ 30%, the hypothesis failed for this model/task mix — retire the flag (with an ADR in docs/decisions/ recording the data) rather than letting a degraded path linger.

## Model bake-off (choosing `TRIPPLANNER_LOCAL_MODEL`)

When more than one candidate model is pulled (e.g. `qwen3.6:latest` vs `qwen3-coder:30b`): run the SAME brief through each (`--model`), review both diffs, log both with `--record-review`. The winner — fewer findings, fewer repair rounds — becomes `TRIPPLANNER_LOCAL_MODEL`. Disk size is not capability: a smaller code-specialized model often beats a larger general one on whole-file rewrites. Revisit the choice at each `/retro` from accumulated log data, not vibes.
