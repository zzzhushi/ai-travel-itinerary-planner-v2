---
name: retro
description: After a milestone ships, review how the WORKFLOW performed and improve the skills themselves. Use after /ship completes, or whenever the process felt wrong ("retro", "why did that milestone go badly", "improve the skills").
---

# Retro: The Skill-Improvement Flywheel

The subject is the **process, not the product** — code findings belong to `/audit`. This skill exists because skills are tuned empirically: the suite improves only if instruction failures observed during a milestone become edits to the skill files.

## Gather evidence (this session + artifacts)

- The milestone's issue, PR, and commit history: where did plans change mid-flight? Which tasks blew their complexity rating (a "mechanical" task that took 3 attempts was misrated — why)?
- Guardrail events: tripwire hook warnings, blocked-stop events, escalations under the blocker protocol. Each is either the system working or an instruction that was unclear — classify which.
- HITL friction: where did the user have to correct course? Every correction is a skill gap — which skill should have prevented it, and what sentence was missing or ignored?
- If `--parallel` ran: wave shapes vs. actual conflicts; re-run rate; was the curated-brief discipline followed?
- If `--local` ran: read `.local-llm-log.jsonl`; apply the decision rule in implement-task's local-llm.md (≥2 median review findings or ≥30% rejection after ~10 runs → recommend retiring the flag).

## Classify each finding

1. **Instruction ignored** → the instruction needs enforcement (hook/permission/artifact), not more prose — rewriting it longer won't help.
2. **Instruction ambiguous** → rewrite as a decision rule with a concrete threshold.
3. **Instruction missing** → add it; if it generalizes beyond this project, note it for the promoted suite.
4. **Instruction wrong** → the process said X, reality wanted Y; change the skill, record why.

## Apply

Propose concrete diffs to files in `.claude/skills/` (and hooks/standards if implicated) — actual edits, not observations. User approves; commit with a message naming the milestone that motivated each change. Keep a short running log in `docs/retro-log.md` (date, milestone, top finding, change made) so trends across milestones are visible — three retros flagging the same skill means its design is wrong, not its wording.

## Discipline

Resist the urge to add prose to every skill every retro — skills accrete flab fast, and principle #2 of the suite is lean SKILL.md. Prefer: delete an ignored instruction and replace it with a hook; tighten a rule rather than appending a caveat. A retro that *removes* lines is usually a better retro.
