# Retro log

One entry per milestone, newest first. Each change names the skill it touched.
Three entries flagging the same skill = its **design** is wrong, not its wording.

## Skill-suite upgrade — user-initiated (2026-07-02)

Not a milestone retro (M3's still runs post-merge and may amend). The user's review: the pipeline "implements correct-working code" but misses senior-engineer behavior — no design step, no refactor discipline, gold-plating, giant batches. Changes, each evidence-backed:

Applied:
- **No design leg — contract decisions made silently in code** (M3: 409-vs-201 decided inside `post_schedule`; anchor-window interaction missed at design time; `pushback.py` layered into `domain/`) → `implement-task` step 1: design note (3–8 lines) for standard/complex posted to the sub-issue before implementing; **4 sync-pause triggers** (contract change · new dep · design-doc deviation · knowing tech debt); `build-milestone` blocker protocol mirrors them.
- **No refactor leg / duplication at write time** (`_hhmm`×2, `TravelMinutes`×4 deferred to nowhere) → ponytail-style **decision-ladder guardrail** before any new code; **prep refactors** in-scope as own `refactor:` commits; the old "no refactoring while you're there" rule rewritten — clean what you modify, leave adjacent code alone; **ceiling comments** (scoped).
- **Deferred findings evaporate in PR comments** → `docs/debt.md` ledger (debt-to-the-ledger guardrail), 3rd-sighting promotion rule; `/milestones` Gate 2 reads it; `/ship` routes findings there.
- **Local-LLM measurement loop broken** (9/14 log rows missing review fields — decision rule uncomputable; 2 malformed detached review rows) → `local_task.py`: `--verify-cmd` runs verify + ≤2 repair rounds in-harness (one complete record, non-zero exit on fail), `--record-review` logs the verdict keyed to the run ts; `local-llm.md`: review-logging is a named step with the exact command; model bake-off protocol added.
- **Batch size** (whole-milestone branches; M3's reviewable stack was hand-rolled) → `build-milestone --subissues` = sub-issue per task + stacked draft PRs (base = failing exit-criteria tests; groups ≤3 tasks / ~500 lines; merge bottom-up when top is green); fresh-eyes runs **per PR** (displaces the end-of-milestone pass); reviewers read via `git show ref:path`, never checkout in the shared tree (M3 incident).
- **`--parallel` never used in 4 milestones** → removed, with its 2 reference files. If parallel exec returns, copy Superpowers' fresh-worktree + two-stage-review design.
- **Architecture sketch got buried in an issue** → design at three altitudes: living `docs/design-doc.md` (Gate 1, seeded from ADRs 001–007), ~10-line Design section per milestone issue, 3–8-line design note per task sub-issue.
- **PRD should grill deeper, with reasoning** (user, importing grill-me) → every question carries a recommendation; three-more-questions rule; 10 lenses (pre-mortem, inversion, do-nothing baseline, 10x/10%, Chesterton's fence...); hand-waving protocol; existence check ("what does 80% of this today?"); decisions log records alternatives + why + would-change-if; template gains Top risks & assumptions (feeds order-by-risk).
- **Per-step executor routing made explicit** (`implement-task`): top model at the joints (design, spec/tests, review), local model in the middle (bulk code-gen) — a wrong test poisons everything downstream; a wrong implementation is caught free by the committed test.
- **Worked example added to `implement-task`** — skills were all rules, no demonstrations; one concrete walk-through beats abstract rule lists (few-shot effect).

Noted, no change:
- Nine-skill pipeline shape confirmed against the landscape (maps ~1:1 onto Superpowers' lifecycle); techniques folded in rather than new skills added.
- Exit-criteria-first, immutable tests, two-lens review, ADR discipline — already senior-grade; untouched.

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
