---
name: prd
description: Interview the user to produce a Product Requirements Document. Use when starting a new product ("write a PRD", "let's scope this idea") or scoping a feature in an existing codebase ("spec out feature X"). Project mode writes docs/prd.md; feature mode writes docs/prds/<feature>.md.
---

# PRD: Requirements Interrogation

You are producing a requirements document by **interviewing the user**, not by drafting one from assumptions. The PRD is the root artifact every later stage reads — an assumption baked in here compounds through every milestone. Depth is the point: a shallow interview produces a confident-looking document built on sand.

## Mode detection

- **Project mode** (empty/new repo, or user describes a whole product) → output `docs/prd.md`.
- **Feature mode** (existing codebase, user describes an addition) → FIRST spawn Explore agents to map relevant existing code (entities, boundaries, conventions), THEN interview with questions grounded in what exists ("you already have X; should this reuse it or diverge?"). Output `docs/prds/<feature-slug>.md`.

Then classify the **project type** — it selects the interview sections and the `/design` mode downstream: **product** (humans use it), **infra/library** (programs and developers use it), **data/ML pipeline**, or **automation/script**. Confirm the classification with the user; record it in the PRD header.

## Interview protocol (the core discipline)

1. **One topic at a time, depth-first.** Pick the most load-bearing unknown, and stay on it until resolved before opening the next. Never present a wall of questions across topics. Drill into an answer before branching to a new topic.
2. **Every question ships with a recommended answer.** Give the user a concrete starting point to react to — "I'd default to X because Y; does that hold for you?" beats an open-ended ask. Use AskUserQuestion with options where the space is enumerable (recommendation first); open questions only where options would anchor.
3. **Should this exist at all?** Early, before requirements accumulate: "What exists today that does 80% of this — why build rather than adopt or wrap it?" Recommending *not building* (or wrapping something) is a valid PRD outcome, and a cheaper one than discovering it at M4.
4. **Never fill a gap with an assumption.** When you hit an unknown, you have exactly two moves: ask the user, or research. If the user doesn't know either ("what do other apps do here?"), research how real products handle it and present 2–3 alternatives **with trade-offs and sources** — never invent "typical" behavior. A burst of more than ~2 searches goes to a subagent that returns the distilled comparison; raw search results never enter the interview context. Investigate what's accessible (the repo, the docs) instead of asking the user about it.
5. **Grill the reasoning, not just the answer.** When the user states a requirement, probe why: what breaks without it, who needs it, what they'd trade it for. Work the lenses in `references/interview-guide.md` (pre-mortem, inversion, do-nothing baseline, 10x/10%...). If two answers contradict, say so immediately and resolve it now.
6. **Call out hand-waving.** "Probably", "we'll figure it out later", "standard behavior" — stop and pin it down, or explicitly park it in Open Questions with an owner. A vague answer recorded as a requirement is an assumption wearing a costume. Paraphrasing ("so what I'm hearing is...") ends inquiry — ask the next question instead.
7. **When you feel you have enough to draft — ask three more questions.** The feeling of readiness is a surface-understanding signal, not a completion signal. The three usually come from unused lenses.
8. **Propose what they haven't considered — as questions.** Walk `references/interview-guide.md` for the topic checklist (auth, persistence, offline, cost ceilings, privacy, failure behavior...). Raise relevant gaps as questions with a recommendation; never silently add requirements.
9. **Capture non-goals as you go.** Everything explicitly cut or deferred goes in Non-goals — this is what stops scope creep in milestones.
10. **Decisions are recorded with their reasoning.** Every decisions-log entry carries: the decision, the alternatives considered, why this one won, and what would change it. A conclusion without its reasoning can't be safely revisited — future sessions re-litigate or blindly obey. Genuine forks additionally get an ADR (`docs/decisions/NNN-slug.md`, template in the milestones skill), linked from the table.

## Scope rule (hard boundary)

The PRD records **what, for whom, why, success criteria, non-goals, top risks**, plus three technical anchors: data entities, external integrations, and hard constraints (cost ceilings, "runs locally", latency). It contains **no architecture, no file layouts, no framework choices** — those are decided at the design-doc stage, after requirements are known. If the user pushes architecture into the PRD, record it under Constraints only if it is genuinely a constraint ("must run on my Mac"), otherwise note it as a preference for the design stage.

## Output and gate

Write the document from `references/prd-template.md`. Convergence test before drafting: could someone name the concrete next actions from this interview? If not, keep grilling. Walk the user through the draft section by section, get explicit approval, then save. The PRD is versioned — material changes later go through this skill again (feature mode), not ad-hoc edits.
