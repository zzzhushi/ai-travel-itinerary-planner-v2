# PRD template

```markdown
# PRD: <product / feature name>
Status: draft | approved · Date: <YYYY-MM-DD> · Mode: project | feature · Type: product | infra | data | automation

## Problem
Who hurts, when, and how badly. Concrete scenario, not a persona poster.

## Users
Primary user(s) and what they're doing the moment they reach for this.

## Goals & success criteria
What "working" means, observably. Each criterion is checkable:
- e.g. "A first-time user completes the core task in under 2 minutes."

## Non-goals
Explicitly cut or deferred, with one line of why. This section earns its length.

## Core flows
The 2–5 journeys that must work, step by step from the user's point of view.

## Requirements
Grouped by flow/area. Each requirement states behavior, not implementation.
Mark must-have vs nice-to-have.

## Data entities
The nouns and their key relationships (NOT a schema): Trip, Day, Activity...

## External integrations
Services this talks to (LLM provider, maps, weather...) and what each is for.
For each: what happens when it's down (ties to graceful degradation later).

## Hard constraints
Cost ceilings, privacy requirements, "must run locally", latency bounds.

## Open questions
Unresolved items, each with an owner (user decision vs research task).

## Decisions log
One-line Q&A pairs from the interview that explain WHY requirements are what
they are. Decisions where a real alternative was weighed link to their ADR:
| decision | why | ADR |
Future sessions read this instead of re-asking.
```

Notes for the author:
- Success criteria and non-goals are the two sections later stages lean on most; spend interview time accordingly.
- The decisions log is what makes this durable across cold-start sessions — record reasoning, not just conclusions.
