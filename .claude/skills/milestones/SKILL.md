---
name: milestones
description: Turn an approved PRD into an architecture sketch (approved first) and vertically-sliced milestones with exit criteria, task decomposition with complexity/model routing metadata, and one GitHub issue per milestone. Use after PRD (and design, if applicable) approval ("plan milestones", "break this down", "create the roadmap").
---

# Milestones: Architecture Gate, then Vertical Slices

Two human gates in this skill, in order: architecture first, slicing second. A bad architecture choice silently shapes every slice — it gets looked at on its own, never bundled into roadmap approval.

## Inputs

Read the PRD, `docs/design/` artifacts if present, and `docs/engineering-standards.md`. In an existing codebase, Explore the current structure first.

## Gate 1 — Architecture sketch (one page, approved before any slicing)

Architecture = the decisions **expensive to reverse**: system shape, what stores the data and who owns the schema, module boundaries and dependency direction, framework/runtime, sync-vs-async integration. (File names and function signatures are not architecture — leave them to implementation.) Propose the sketch with one-line rationale per decision; where a real alternative was seriously weighed, write an ADR (`references/adr-template.md`) in `docs/decisions/NNN-slug.md`. User approves the sketch before you slice.

## Gate 2 — Slicing

1. **Vertical only.** Every milestone ends with something a human can run and judge — the **demo sentence**: for products "user does X and sees Y"; for infra/data "a client invokes X and gets Y" (curl, example client code, one file through the pipeline). If the demo sentence starts with "the code now has...", it's horizontal; re-slice. A **cross-cutting layer** (API, UI, persistence) built all at once is the subtle horizontal trap — distribute it across the milestones where it first lets a human *do something new*, neither bundled at the end (big-bang) nor built over not-yet-real state (premature). Infra exit criteria may include SLO checks and failure injection.
2. **Milestone 0 is always scaffolding** — exactly the machinery every milestone consumes (env/deps, test runner, lint, types, logging setup, pre-commit, CI with coverage ratchet, hook activation), proven by a walking skeleton: one hello-world slice through the whole toolchain passing CI. Never pre-build what only a future milestone needs; extension *patterns* live in the standards doc.
3. **Sizing:** a milestone decomposes into **≤10 tasks** or it splits (prefer 4–7). If later reconciliation in `/build-milestone` reveals more, the protocol is: shrink the demo sentence, deliver the smaller slice, spin the remainder into a NEW issue inserted in the roadmap — identity lives in issue numbers, never sub-numbering (no "m1.5").
4. **Order by risk:** the milestone testing the riskiest assumption comes right after scaffolding.

## Task metadata (the routing classifier — workers never self-assess)

Each task carries `complexity` (mechanical | standard | complex), `executor` (local | opus), `why`, `depends_on`. Mechanical (boilerplate/config following a pattern) and standard (a new feature copying an established pattern, fully specified) → **local model** (Ollama; cloud sonnet/haiku fallback if it's unavailable), always behind a mandatory top-model review before commit. Complex (novel algorithm, concurrency, security surface, or ANY ambiguity) → **opus + extended thinking**, regardless of size. **Routability test:** route to local only if the task's failing test could be written right now; otherwise it's complex — fix the spec, don't route down. (Legacy roadmap rows that say haiku/sonnet map to `local`; opus maps to `opus`.)

## Output

After both approvals: write `docs/roadmap.md` (`references/roadmap-template.md`) and create one GitHub issue per milestone (`gh issue create`, body via temp file, from `references/issue-template.md`). Record issue numbers back into the roadmap.
