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

Write the failing tests that prove each exit criterion, plus a manual validation script/checklist for criteria tests can't capture (visual quality, feel). Run them; confirm they fail for the right reason. **Commit them.** These tests are now immutable: any change to them requires user approval, never silent edits.

## Step 2 — Confirm the task plan

The issue carries tasks with complexity/model metadata from `/milestones`. Reconcile against current code reality; if a task turned out under-specified or new tasks emerged, update the issue body (`gh issue edit`, body via temp file). With `--subissues`: create one sub-issue per task linked to the milestone issue instead of a checklist.

## Step 3 — Execute tasks

**Sequential (default):** for each task in dependency order — invoke the `implement-task` skill and follow its loop yourself. One task, one commit, tick the checklist.

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
