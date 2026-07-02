---
name: implement-task
description: The single-task implementation discipline — design note, test-first, decision ladder, guarded, reviewed, committed. Invoked by /build-milestone per task, or used standalone for one-off tasks ("implement-task add a --currency flag", optionally --local for local-LLM routing of mechanical tasks).
---

# Implement Task

This skill is **self-contained by design**: subagents receive it cold, with no conversation history. Everything needed to do one task correctly is here or in the task brief.

## Inputs

A task brief containing: the task description, its complexity/executor rating, the milestone exit criteria it serves, intended file paths, relevant interfaces/conventions, and `depends_on` state. Standalone use (a user types `/implement-task <description>`): construct the brief yourself — read `docs/engineering-standards.md`, `docs/design-doc.md`, and the relevant code first; if the task is ambiguous, ask before coding.

## The loop

Executor routing principle: **top model at the joints (design, spec, review) — local model in the middle (bulk code-gen)**. A wrong design note or wrong test poisons every downstream token; a wrong implementation is caught free by the committed test.

1. **Plan the task** *(session model — never delegate thinking)*. Write down: the task in your own words + the exact file list you intend to touch. For standard/complex tasks add a **design note (3–8 lines)**: the approach; one alternative you rejected and why; for any new module, its layer and what it may import; contract impact. Post the note to the task's sub-issue (or your response) BEFORE implementing. Work outside the declared file list = stop and flag scope creep.
   **Sync pause — stop, present a recommendation, and wait for the user — on any of four triggers:**
   - the task changes a **public contract** (HTTP status/shape, CLI flags/output, anything in `docs/api-contract.md`)
   - a **new dependency**
   - a **deviation from `docs/design-doc.md`** (architecture, layering, data ownership)
   - a shortcut that **knowingly creates tech debt**
2. **Failing test first** *(top model for complex/exit-criteria tasks; the test is the spec and is immutable — the worst place to economize)*. If the behavior isn't already pinned by a committed failing test, write one now and watch it fail for the right reason. **Commit the test before any implementation code** — the standalone test commit is the rollback anchor: `git reset --hard <test-commit>` discards a bad attempt cleanly. Can't write the failing test? The task is under-specified — escalate, don't improvise. (UI/visual tasks: write the manual validation step instead.)
3. **Implement via the decision ladder** *(local executor for mechanical/standard; top model inline for complex)*. Before writing ANY new code, walk the ladder — an internal checklist, zero user interruptions:
   (a) should this exist at all? → (b) does the codebase already have it? search first → (c) stdlib? → (d) platform natives (DB constraints, framework features)? → (e) existing deps? → (f) only then write minimal new code.
   Deletion over addition; boring over clever. **Prep refactors are in-scope**: if a small refactor *within the files you're touching* makes the change cleaner, do it FIRST as its own `refactor:` commit — make the change easy, then make the easy change. Intentional simplifications get a **ceiling comment** where a reviewer would plausibly flag them (see guardrails).
4. **Verify** *(no model — deterministic)*: run the project's verify command (CLAUDE.md § Conventions). Repair rounds stay on the step-3 executor; same error surviving 3 distinct fix attempts (2 for local runs) → stop, write a diagnosis, escalate.
5. **Review, then commit** *(top-model review mandatory — ~200 tokens that catch 20k-token mistakes; never delegate judgment)*. Review the diff against the design note and guardrails: convention violations, hardcoding, gold-plating, layering. Residual cleanups → fix now if within touched files, else `docs/debt.md`. Commit: 1–3 sentences, what + the non-obvious why. Tick the task / close the sub-issue.

## Worked example (the loop on a real task)

Task: "add `--format json` to the CLI schedule command" (standard/local).

> **1 — Plan** (posted to sub-issue): Touch `src/tripplanner/cli.py`, `tests/test_entrypoints.py`. Approach: `--format {text,json}` argparse choice, default `text`; JSON path dumps the presenter's dict form. Rejected: a second `schedule-json` subcommand — duplicates parsing for no gain. No new module, no contract change (CLI *addition*, backward compatible — noting in api-contract.md CLI column anyway). No sync trigger.
> **2 — Test**: `test_schedule_format_json_emits_parseable_json` — invokes `main(["schedule", fixture, "--format", "json"])`, asserts `json.loads(capsys.out)["days"]` has 1 day. Committed alone: `test: pin --format json output shape`. Fails: `unrecognized arguments: --format`.
> **3 — Ladder**: (b) codebase already has `format_itinerary` (text) — reuse its structure; does a dict-shaping helper exist? No, but `Itinerary` is a dataclass → (c) stdlib `dataclasses.asdict` does the job. No new helper written.
> **4 — Verify**: green on round 1.
> **5 — Review**: diff matches note; one finding — `asdict` leaks `Coord` nesting the test didn't pin; acceptable, ceiling comment added (`# asdict shape = internal dataclass layout; freeze a schema if this becomes an API`). Commit: `feat(cli): --format json on schedule. asdict over hand-rolled dict — no schema promise yet.`

## Hard rules

Read `references/guardrails.md` before step 3 the first time, and whenever tempted to bend one. The unbendable three: never weaken/delete/skip a test to make it pass; never add `# noqa` / `# type: ignore` / skip-markers without an adjacent justification comment; never add a dependency without surfacing it first.

## Local-LLM routing (default executor when Ollama is available)

For tasks rated **mechanical or standard** by default; complex tasks are eligible when committed tests fully pin the behavior (see `references/local-llm.md`). When Ollama is available this is the **default** executor; without it, fall back to a sonnet subagent. The standalone `--local` flag forces this path for a one-off task. Process in `references/local-llm.md`; mechanics in `scripts/local_task.py` (run with `--verify-cmd` so verification and repair happen in-harness). **Every local run is followed by the mandatory top-model review (step 5) before commit, and the review is logged** via `--record-review` — an unlogged review breaks the experiment's decision rule.
