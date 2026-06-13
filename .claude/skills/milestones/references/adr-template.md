# ADR template (docs/decisions/NNN-slug.md)

One file per decision **where a real alternative was seriously considered** — that's the gate. Routine choices stay as one-liners in the PRD decisions log. Number sequentially (001, 002...); add a line to `docs/decisions/README.md`.

```markdown
# ADR-NNN: <decision as a short imperative, e.g. "Store records in SQLite">
Status: proposed | accepted | superseded by ADR-MMM · Date: <YYYY-MM-DD>

## Context
What forced this decision now — the requirement, constraint, or fork in the
road. 2–5 sentences; enough that a stranger sees why "just pick one" wasn't free.

## Options considered
For each real option (2–3): one line of what it is, then honest pros/cons.
Include the option NOT chosen at its strongest — a strawman here makes the
record worthless.

## Decision
What was chosen and the one or two reasons that actually tipped it.

## Consequences
What this commits us to: what gets easier, what gets harder, what would make
us revisit (the trigger for a superseding ADR).
```

Rules:
- Never delete or rewrite an accepted ADR — supersede it with a new one and update the Status line. The history of changed minds is the most valuable part.
- Write it when the decision is made (PRD interview, architecture gate, or mid-build escalation), not retrospectively — reasoning evaporates fast.
