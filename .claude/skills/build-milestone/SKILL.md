---
name: build-milestone
description: Execute one milestone end-to-end from its GitHub issue — exit-criteria tests first, task loop, per-PR fresh-eyes verification. Usage - "build-milestone <issue-number>" with optional flag --subissues (sub-issue per task + stacked draft PRs instead of a single milestone branch).
---

# Build Milestone

You are the orchestrator for one milestone: you run each task through the `implement-task` loop in dependency order, keep the milestone issue current, and verify the result with fresh eyes.

## Startup

1. `gh issue view <n>` — the issue is the contract. Read also: `docs/roadmap.md` (this milestone's section), `docs/design-doc.md` (the system design doc — deviations from it are a sync-pause trigger), `docs/prd.md`, `docs/design/design-system.md` (if UI work), `docs/engineering-standards.md`, and the relevant existing code (Explore agents for anything non-trivial — they return reports, you keep context lean). If the issue has a Design section, refine it against current code reality; if the milestone touches architecture and has none, write one now (~10 lines) and update the issue.
2. Branch: `git checkout -b milestone-<n>-<slug>` from up-to-date main.

## Step 1 — Encode the exit criteria (before any feature code)

Write the failing tests that prove each exit criterion, plus a manual validation script/checklist for criteria tests can't capture (visual quality, feel). Run them; confirm they fail for the right reason. **Commit them in their own commit** — no implementation code in this commit. These tests are now immutable: any change to them requires user approval, never silent edits. The test commit is also the repair anchor for local-LLM runs. Format them before committing so a later auto-format/pre-commit never touches them; if a formatter *does* edit an immutable test, the **config** is wrong — fix the config and restore the test, never accept the edit.

## Step 2 — Confirm the task plan

The issue carries tasks with complexity/executor metadata from `/milestones`. Reconcile against current code reality; if a task turned out under-specified or new tasks emerged, update the issue body (`gh issue edit`, body via temp file). If reconciliation reveals **more than 10 real tasks**, don't grow the milestone: shrink its demo sentence, deliver the smaller vertical slice, and spin the remainder into a new milestone issue inserted in the roadmap (never sub-number).

**With `--subissues`:** create **one sub-issue per task** linked to the milestone issue (not one per group — the sub-issue is where the task's design note lands and where progress is tracked). Then group tasks into **PR groups**: ≤3 coupled tasks each, split any group whose diff would exceed ~500 lines. The PR structure is **stacked drafts**:

- **Base PR** = the Step-1 exit-criteria test commit ONLY, branched from main. Red CI by design — that is the honest TDD signal, not a defect.
- **One draft PR per group**, each branching off the previous PR's branch, closing its tasks' sub-issues.
- Intermediate PRs stay red until the feature satisfying a given exit test lands; the **top of the stack must be fully green**.
- **Merge bottom-up only when the top is green** (each merge retargets the next PR onto main).

Without the flag: single milestone branch, task checklist in the issue body, one PR at the end.

## Step 3 — Execute tasks

For each task in dependency order, run the full `implement-task` loop — including its design note, sync-pause triggers, decision ladder, and mandatory review. Executor routing comes from the task's metadata:

- **Complex → code it inline yourself** (full context — best on gnarly algorithms).
- **Mechanical/standard → the local executor:** curate the brief (full file text or `--no-read`-safe, no placeholders), run
  `.claude/skills/implement-task/scripts/local_task.py --brief <f> --allow <paths> --verify-cmd "<the verify line from CLAUDE.md>"` —
  the harness verifies and auto-repairs up to 2 rounds itself and exits non-zero if still red (then implement on cloud). **Review the diff before commit** (mandatory gate) and **log the verdict** with `--record-review` — an unlogged review breaks the experiment's decision rule. Ollama down or harness gave up → subagent at the task's cloud tier (Agent tool `model:` param — mechanical → haiku, standard → sonnet), never the session model.

Either way: one logical unit, one commit (coupled tasks commit together — name them); prep refactors land as their own `refactor:` commits first. Tick the checklist / close the sub-issue. Per-task cost stays visible — local runs log to `.local-llm-log.jsonl`, cloud subagents report their tokens.

## Context economy (subagents vs inline)

Subagents protect the orchestrator's **context window**, not the token bill — a subagent's usage is still billed, often more in total; what it buys is a lean main context, longer sessions, and better cache hits. Route work to a subagent when all three hold: **bulky input** (many files, long diffs, search results) · **small output** (a report, a verdict, a diff) · **separable** (a cold start with a curated brief loses nothing). That covers: Explore/research sweeps, fresh-eyes and code review, cloud-fallback implementation of well-specified tasks, log/audit analysis. Keep inline: anything needing accumulated conversation context or the user's in-session guidance, triage and merge judgment across tasks, and edits small enough that writing the brief costs more than the work. Always pass `model:` explicitly on spawn — a subagent that inherits the session model silently un-does the routing table.

## Step 4 — Fresh-eyes verification

Spawn a verification subagent (`model: sonnet` — spec-compliance checking against a written issue doesn't need the top tier; the adversarial `/code-review` at ship stays top-model) whose prompt contains ONLY the issue text and the diff — explicitly not your conversation. Its job: spec gaps and corner-cutting (weakened/assertion-free tests, hardcoded values that should be derived, swallowed errors, suppression comments, unrequested scope/gold-plating). Triage its findings: fix real ones, route disputed/deferred ones to `docs/debt.md`.

- **Stacked mode: run fresh-eyes per PR**, on each PR's own delta (`gh pr diff <n>`), as each group completes — bugs surface while the group's context is fresh, not after the whole milestone. No end-of-milestone repeat pass.
- **Single-branch mode:** one pass when all exit-criteria tests are green, on `git diff main...HEAD`.
- Verification subagents **never `git checkout` in the shared working tree** — a parallel reviewer switching branches corrupts the orchestrator's state. Read code at a ref with `git show <ref>:<path>` or `gh pr diff`.

## Step 5 — Close out

Run the manual validation steps from the issue yourself where possible; report results faithfully. Update the issue checklist / sub-issues to final state. Hand off to `/ship` (stacked mode: `/ship` merges the stack bottom-up).

## Blocker protocol (stop and surface to the user when)

- A task hits a **sync-pause trigger** (from implement-task step 1): public contract change · new dependency · deviation from `docs/design-doc.md` · a shortcut that knowingly creates tech debt. Present a recommendation, wait.
- Same error survives 3 genuinely different fix attempts (include diagnosis: tried, observed, hypothesis).
- A credential, account, payment, or external setup is needed.
- The spec is ambiguous or self-contradictory in a way that changes the implementation.
- A fix would require weakening an exit criterion or test — never do this silently.
