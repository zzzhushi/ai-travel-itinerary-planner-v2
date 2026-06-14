---
name: build-milestone
description: Execute one milestone end-to-end from its GitHub issue — exit-criteria tests first, task loop, fresh-eyes verification. Usage - "build-milestone <issue-number>" with optional flags --parallel (worktree wave execution) and --subissues (sub-issue per task instead of checklist).
---

# Build Milestone

You are the orchestrator for one milestone. In sequential mode (default) you also do the implementation; with `--parallel` you **never write code** — you dispatch, monitor, merge, and verify.

## Startup

1. `gh issue view <n>` — the issue is the contract. Read also: `docs/roadmap.md` (this milestone's section), `docs/prd.md`, `docs/design/design-system.md` (if UI work), `docs/engineering-standards.md`, and the relevant existing code (Explore agents for anything non-trivial — they return reports, you keep context lean).
2. Branch: `git checkout -b milestone-<n>-<slug>` from up-to-date main.

## Step 1 — Encode the exit criteria (before any feature code)

Write the failing tests that prove each exit criterion, plus a manual validation script/checklist for criteria tests can't capture (visual quality, feel). Run them; confirm they fail for the right reason. **Commit them.** These tests are now immutable: any change to them requires user approval, never silent edits. Format them before committing so a later auto-format/pre-commit never touches them; if a formatter *does* edit an immutable test, the **config** is wrong — fix the config and restore the test, never accept the edit.

## Step 2 — Confirm the task plan

The issue carries tasks with complexity/model metadata from `/milestones`. Reconcile against current code reality; if a task turned out under-specified or new tasks emerged, update the issue body (`gh issue edit`, body via temp file). If reconciliation reveals **more than 10 real tasks**, don't grow the milestone: shrink its demo sentence, deliver the smaller vertical slice, and spin the remainder into a new milestone issue inserted in the roadmap (never sub-number). With `--subissues`: create one sub-issue per task linked to the milestone issue instead of a checklist.

## Step 3 — Execute tasks

**Sequential (default):** for each task in dependency order, follow the `implement-task` loop, routed by the task's executor. **Complex → code it inline yourself** (full context — best on gnarly algorithms). **Mechanical/standard → the local executor:** curate the brief (full file text, no placeholders), run `scripts/local_task.py --brief <f> --allow <paths>`, verify (`uv run ruff check && uv run mypy && uv run pytest -q`); if verify fails, re-run with `--repair-log <output_file>` up to 2 times before falling back to cloud. Then **review the diff before commit** (mandatory gate); fall back to a sonnet subagent if Ollama is down. Either way: one logical unit, one commit (coupled tasks commit together — name them), tick the checklist. This keeps the routing metadata real (it was inert when sequential mode coded everything inline at the session model) and surfaces per-task cost — local runs log to `.local-llm-log.jsonl`, cloud subagents report their tokens.

**`--parallel`:** read `references/parallel-execution.md`. Group tasks into dependency waves; within a wave, spawn one general-purpose subagent per task (Agent tool, `isolation: "worktree"`, model from task metadata, all spawns in one message). Each prompt is a **curated brief**: task spec + exact files + interface signatures + the few conventions that matter + the full text of the implement-task skill's loop and hard rules + "do not re-explore broadly; do not touch files outside your list". Then merge per `references/merge-protocol.md` — one branch at a time, full test suite between merges.

## Step 4 — Fresh-eyes verification

When all exit-criteria tests pass: spawn a verification subagent whose prompt contains ONLY the issue text and `git diff main...HEAD` — explicitly not your conversation. Its job: spec gaps and corner-cutting (weakened/assertion-free tests, hardcoded values that should be derived, swallowed errors, suppression comments, unrequested scope). Triage its findings: fix real ones, record disputed ones for the user.

## Step 5 — Close out

Run the manual validation steps from the issue yourself where possible; report results faithfully. Update the issue checklist to final state. Hand off to `/ship`.

## Blocker protocol (stop and surface to the user when)

- Same error survives 3 genuinely different fix attempts (include diagnosis: tried, observed, hypothesis).
- A credential, account, payment, or external setup is needed.
- The spec is ambiguous or self-contradictory in a way that changes the implementation.
- A fix would require weakening an exit criterion or test — never do this silently.
