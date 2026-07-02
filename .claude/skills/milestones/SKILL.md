---
name: milestones
description: Turn an approved PRD into a system design doc (approved first) and vertically-sliced milestones with exit criteria, task decomposition with complexity/executor routing metadata, and one GitHub issue per milestone. Use after PRD (and design, if applicable) approval ("plan milestones", "break this down", "create the roadmap").
---

# Milestones: Design Gate, then Vertical Slices

Two human gates in this skill, in order: system design first, slicing second. A bad architecture choice silently shapes every slice — it gets looked at on its own, never bundled into roadmap approval.

## Inputs

Read the PRD (including its Top risks & assumptions), `docs/design/` artifacts if present, and `docs/engineering-standards.md`. In an existing codebase, Explore the current structure first.

## Design at three altitudes

Design lives at three levels; each records only what its parent doesn't answer — no repetition:

| Level | Artifact | Written | Size |
|---|---|---|---|
| **Project** | `docs/design-doc.md` — living system design doc | Gate 1; updated when architecture shifts | ~2 pages |
| **Milestone** | "Design" section in the milestone issue — this slice's approach, what it adds/changes in the project doc | Gate 2 slicing; refined at build-milestone startup | ~10 lines |
| **Task** | Design note in the sub-issue | implement-task step 1 | 3–8 lines |

## Gate 1 — System design doc (approved before any slicing)

Write `docs/design-doc.md`. It records the decisions **expensive to reverse** plus the shared context every later implementer needs; file names and function signatures are not design — leave them to implementation. Sections (most are 5–10 lines):

- **Context & goals** — one-paragraph recap tying to the PRD.
- **Architecture** — components and data flow (system shape, module boundaries, dependency direction, framework/runtime, sync-vs-async integration).
- **Data model** — entities, ownership, lifecycle (not a schema).
- **Interface contracts** — pointer to `docs/api-contract.md` + error semantics.
- **Key decisions** — each with the alternative rejected and why; genuine forks get an ADR (`references/adr-template.md`, `docs/decisions/NNN-slug.md`) and a link.
- **Cross-cutting concerns** — error handling, observability, security, performance budgets.
- **Risks & mitigations** — seeded from the PRD's Top risks.
- **Open questions** — each with an owner.

The doc is **living**: a milestone that shifts architecture updates it in the same PR (deviating without updating it is a sync-pause trigger in implement-task). User approves the doc before you slice; material later changes come back through this gate.

## Gate 2 — Slicing

1. **Vertical only.** Every milestone ends with something a human can run and judge — the **demo sentence**: for products "user does X and sees Y"; for infra/data "a client invokes X and gets Y" (curl, example client code, one file through the pipeline). If the demo sentence starts with "the code now has...", it's horizontal; re-slice. A **cross-cutting layer** (API, UI, persistence) built all at once is the subtle horizontal trap — distribute it across the milestones where it first lets a human *do something new*, neither bundled at the end (big-bang) nor built over not-yet-real state (premature). Infra exit criteria may include SLO checks and failure injection.
2. **Milestone 0 is always scaffolding** — exactly the machinery every milestone consumes (env/deps, test runner, lint, types, logging setup, pre-commit, CI with coverage gate, hook activation), proven by a walking skeleton: one hello-world slice through the whole toolchain passing CI. Never pre-build what only a future milestone needs; extension *patterns* live in the standards doc.
3. **Sizing:** a milestone decomposes into **≤10 tasks** or it splits (prefer 4–7). If later reconciliation in `/build-milestone` reveals more, the protocol is: shrink the demo sentence, deliver the smaller slice, spin the remainder into a NEW issue inserted in the roadmap — identity lives in issue numbers, never sub-numbering (no "m1.5").
4. **Order by risk:** the milestone testing the riskiest assumption (see the PRD's Top risks) comes right after scaffolding.
5. **Read `docs/debt.md`:** any ledger item at its promotion trigger (3rd sighting) becomes a real task in the next milestone — debt scheduling is part of slicing, not a someday-pile.
6. **Milestone Design section:** each issue gets ~10 lines — the slice's technical approach and what (if anything) it adds or changes in `docs/design-doc.md`.

## Task metadata (the routing classifier — workers never self-assess)

Each task carries `complexity` (mechanical | standard | complex), `executor`, `why`, `depends_on`. The executor names the exact tier so the orchestrator never burns top-model tokens on work a cheaper tier does equally well — and never routes ambiguity down to save tokens:

| complexity | executor | cloud fallback (Ollama down) |
|---|---|---|
| mechanical — boilerplate/config following a pattern | `local` | haiku subagent |
| standard — new feature copying an established pattern, fully specified | `local` | sonnet subagent |
| complex — novel algorithm, concurrency, security surface, or ANY ambiguity | `opus` inline + extended thinking, regardless of size | — |

Every local/fallback run sits behind the mandatory top-model diff review before commit (implement-task step 5) — the review is where top-model tokens are spent on cheap-tier work, deliberately. **Routability test:** route to local only if the task's failing test could be written right now; otherwise it's complex — fix the spec, don't route down. (Legacy roadmap rows that say haiku/sonnet map to `local`; opus maps to `opus`.)

## Output

After both approvals: write `docs/roadmap.md` (`references/roadmap-template.md`) and create one GitHub issue per milestone (`gh issue create`, body via temp file, from `references/issue-template.md` — including its Design section). Record issue numbers back into the roadmap.
