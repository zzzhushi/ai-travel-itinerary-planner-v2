---
name: prd
description: Interview the user to produce a Product Requirements Document. Use when starting a new product ("write a PRD", "let's scope this idea") or scoping a feature in an existing codebase ("spec out feature X"). Project mode writes docs/prd.md; feature mode writes docs/prds/<feature>.md.
---

# PRD: Requirements Interrogation

You are producing a requirements document by **interviewing the user**, not by drafting one from assumptions. The PRD is the root artifact every later stage reads — an assumption baked in here compounds through every milestone.

## Mode detection

- **Project mode** (empty/new repo, or user describes a whole product) → output `docs/prd.md`.
- **Feature mode** (existing codebase, user describes an addition) → FIRST spawn Explore agents to map relevant existing code (entities, boundaries, conventions), THEN interview with questions grounded in what exists ("you already have X; should this reuse it or diverge?"). Output `docs/prds/<feature-slug>.md`.

Then classify the **project type** — it selects the interview sections and the `/design` mode downstream: **product** (humans use it), **infra/library** (programs and developers use it), **data/ML pipeline**, or **automation/script**. Confirm the classification with the user; record it in the PRD header.

## Interview protocol (the core discipline)

1. **One topic at a time, depth-first.** Pick the most load-bearing unknown, and stay on it until resolved before opening the next. Never present a wall of questions across topics. Use AskUserQuestion with concrete options where possible; open questions where options would anchor.
2. **Never fill a gap with an assumption.** When you hit an unknown, you have exactly two moves: ask the user, or research. If the user doesn't know either ("what do other apps do here?"), research how real products handle it and present 2–3 alternatives **with trade-offs and sources** — never invent "typical" behavior. A burst of more than ~2 searches goes to a subagent that returns the distilled comparison; raw search results never enter the interview context.
3. **Grill the reasoning, not just the answer.** When the user states a requirement, probe why: what breaks without it, who needs it, what they'd trade it for. If two answers contradict, say so immediately and resolve it now.
4. **Propose what they haven't considered — as questions.** Walk `references/interview-guide.md` for the topic checklist (auth, persistence, offline, cost ceilings, privacy, failure behavior...). Raise relevant gaps as questions with a recommendation; never silently add requirements.
5. **Capture non-goals as you go.** Everything explicitly cut or deferred goes in Non-goals — this is what stops scope creep in milestones.
6. **Decisions with a real fork get an ADR.** When a genuine alternative was seriously weighed, write `docs/decisions/NNN-slug.md` (template in the milestones skill) and link it from the PRD's decisions-log table. Routine Q&A stays a one-line table entry — the gate is "was there a real alternative", never "every decision".

## Scope rule (hard boundary)

The PRD records **what, for whom, why, success criteria, non-goals**, plus three technical anchors: data entities, external integrations, and hard constraints (cost ceilings, "runs locally", latency). It contains **no architecture, no file layouts, no framework choices** — those are decided at milestone time, after requirements are known. If the user pushes architecture into the PRD, record it under Constraints only if it is genuinely a constraint ("must run on my Mac"), otherwise note it as a preference for the milestone stage.

## Output and gate

Write the document from `references/prd-template.md`. Walk the user through it section by section, get explicit approval, then save. The PRD is versioned — material changes later go through this skill again (feature mode), not ad-hoc edits.
