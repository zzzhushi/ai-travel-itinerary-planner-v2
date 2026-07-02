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

## Top risks & assumptions
At most 3 bullets: the assumptions most likely to sink the project if wrong,
each with how we'd find out early. Feeds the milestone stage's order-by-risk.

## Open questions
Unresolved items, each with an owner (user decision vs research task).

## Decisions log
Entries from the interview that explain WHY requirements are what they are.
Each records: the decision · alternatives considered · why this one won ·
what would change it. Genuine forks link to their ADR:
| decision | alternatives | why | would change if | ADR |
Future sessions read this instead of re-asking — a conclusion without its
reasoning gets re-litigated or blindly obeyed.
```

Notes for the author:
- Success criteria and non-goals are the two sections later stages lean on most; spend interview time accordingly. Phrase each success criterion so a later milestone exit criterion can test it.
- The decisions log is what makes this durable across cold-start sessions — record reasoning, not just conclusions.
