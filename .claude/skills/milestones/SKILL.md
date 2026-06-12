---
name: milestones
description: Break an approved PRD into vertically-sliced milestones with exit criteria, task decomposition with complexity/model routing metadata, and one GitHub issue per milestone. Use after PRD (and design, if UI) approval ("plan milestones", "break this down", "create the roadmap").
---

# Milestones: Vertical Slices with Exit Criteria

You are converting the PRD into an ordered list of **demonstrable product increments**. This stage is also where architecture is decided (deliberately not in the PRD) and where every task gets its complexity rating — workers never self-assess.

## Inputs

Read `docs/prd.md` (or the feature PRD), `docs/design/design-system.md` if present, and `docs/engineering-standards.md`. In an existing codebase, Explore the current structure first.

## Slicing rules

1. **Vertical only.** Every milestone ends with something a human can run and judge: "user gets a 1-day itinerary for one city from the CLI" — never "data layer complete". If a milestone's demo sentence starts with "the code now has...", it's horizontal; re-slice.
2. **Milestone 0 is always scaffolding:** uv + pyproject, pytest, ruff, mypy strict, structlog setup, pre-commit + gitleaks, CI with coverage ratchet, and activation of the repo's test-blocking Stop hook. The quality machinery must exist before feature code.
3. **Sizing:** a milestone decomposes into **≤10 tasks** or it splits. Prefer 4–7.
4. **Order by risk, not convenience:** the milestone that tests the riskiest assumption (usually the LLM-quality core loop) comes right after scaffolding.
5. **Architecture decisions** made here (framework, storage, module boundaries) get one-paragraph notes in `docs/decisions.md`.

## Per-milestone contents (template: `references/roadmap-template.md`)

Goal (the demo sentence) · **Exit criteria** (observable behaviors, each mapped to the test or validation command that proves it) · Validation steps (exact commands/clicks a human runs) · Graceful-degradation behavior for any external dependency introduced · Task list with metadata.

## Task metadata (the routing classifier)

Each task carries: `complexity` (mechanical | standard | complex), `model` (haiku | sonnet | opus), `why` (one line), `depends_on` (task ids).

- **mechanical** — boilerplate/rename/config following an existing pattern → haiku.
- **standard** — new feature copying an established pattern, fully specified → sonnet.
- **complex** — novel algorithm, concurrency, security surface, or ANY ambiguity → opus + extended thinking, regardless of size.
- **Routability test:** a task may be rated below `complex` only if its failing test could be written right now. If not, the task is under-specified — fix the spec, don't route it down.

## Gate and output

Present the roadmap, iterate with the user, get explicit approval. Then write `docs/roadmap.md` and create one GitHub issue per milestone (`gh issue create`) from `references/issue-template.md` — title `Milestone <n>: <goal>`, body with exit criteria, validation steps, and the task checklist. Confirm issue numbers back into the roadmap doc.
