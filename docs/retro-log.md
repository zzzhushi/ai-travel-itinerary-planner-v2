# Retro log

One entry per milestone, newest first. Each change names the skill it touched.
Three entries flagging the same skill = its **design** is wrong, not its wording.

## M2 — Multi-day engine (2026-06-14)

Applied:
- **Complexity label was the wrong routing gate for local-LLM** — M2 eval confirmed complex algorithmic tasks (k-means clustering, `_apply_meals` constraint-slotting) pass cleanly when committed tests are strong and briefs are complete. "Complex tasks never route here" was false. → `local-llm.md`: replaced complexity exclusion with test-gated eligibility; complex tasks now eligible. `implement-task` SKILL.md: updated section header to match.
- **Brief placeholder = silent corruption** — `format_multiday` brief had `<PASTE_FILE>` placeholder; model copied it literally, mangling the output. Every failure traced to brief quality, not model capability. → `local-llm.md` step 1: explicit "full text of every file, no placeholders" rule. `build-milestone` Step 3: explicit "(full file text, no placeholders)" callout in the local executor path.
- **`===END` parser bug** — model writes `===END` (no trailing `===`); original parser left the token in the file body, causing syntax errors. → `local_task.py` `extract_files`: now terminates on `===END===` first, then `===END` — whichever appears first wins.
- **Repair loop existed but never fired** — `--repair-log` was wired in the script but neither `local-llm.md` nor `build-milestone` named the flag or said when to invoke it. → `local-llm.md` step 3 and `build-milestone` Step 3 now name the flag and give the two-round limit explicitly.

Noted, no change:
- **Two-lens verification design held** — Step 4 (spec compliance) caught nothing on M2; `/ship` code-review caught the M1 greedy-selection bug (close-but-late-opening place selected first, wasting morning time). Different lenses both earning their place.
- **n=4 eval, not definitive** — local routing for complex tasks is now *eligible*, not the default; the decision rule in `local-llm.md` (10 logged runs, ≥2 median findings or ≥30% rejection → retire) is the right long-run arbiter.

## M0 — Scaffolding (2026-06-13)

Applied:
- **A formatter edited an immutable exit-criteria test** → `build-milestone` Step 1: format the tests before committing; if a formatter later edits an immutable test, the *config* is wrong — fix the config and restore the test, never accept the edit.
- **"One task, one commit" too rigid for coupled tasks** (T3+T4, T7+T8 shared one test) → `build-milestone` Step 3: "one logical unit, one commit," coupled tasks committed together and named.
- **Standards over-claimed the observability schema** ("every log line carries trace_id" — impossible outside a span) → `engineering-standards`: `correlation_id` on every line; `trace_id`/`span_id` only within a span.
- **Cross-cutting layers tempt a horizontal big-bang** (user insight, raised twice) → `milestones` Gate 2: distribute API/UI/persistence across the milestones where each first lets a human do something new — not bundled at the end, not over not-yet-real state.
- **Telemetry must be agent-debuggable** (user insight; not LLM-specific) → `engineering-standards`: logs serve a human *and* a coding agent that debugs its own output; design fields/events for both.

Token-routing fix (motivated by M0 burning ~all-opus):
- **Sequential mode coded everything inline at the session model, so the per-task `haiku/sonnet/opus` routing never fired** — it was only ever live in `--parallel`. → `build-milestone` Step 3 now routes per task: complex inline on opus, mechanical/standard to the **local executor** (Ollama, mandatory top-model review, sonnet fallback). `milestones` routing changed to `executor: local | opus`; `implement-task` local path extended from mechanical-only to mechanical+standard and made the default for non-complex when Ollama is up. Per-task cost is now visible (local log / subagent tokens). Decision: complex stays inline (quality on hard algorithms) at the cost of those tasks' tokens remaining unmetered.

Noted, no change:
- Stop-hook vs. Step-1 committed-failing-tests — self-resolves via the hook's `stop_hook_active` escape hatch.
- `--subissues` gh mechanics (native link needs `-F` integer id; `gh issue close` is one-at-a-time) — too tool-specific to codify.
- Positive: the two-lens review design worked — Step-4 verification (spec compliance) passed M0, then `/ship`'s `/code-review` (adversarial bug-hunt) caught a real coverage-gate bug. Different lenses, both earning their place.
