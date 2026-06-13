# Interview guide — topic checklists and question craft

Work the **common core** first, then the section for the classified project type. Raise relevant topics as questions with a recommendation; skip inapplicable ones, but say you're skipping them and why.

## Common core (every project type)

1. **The triggering moment** — "Walk me through the last time you actually needed this. What did you do instead?" (Grounds everything in a real scenario; kills imagined requirements.)
2. **Audience size** — just the user, or others? Changes auth, polish bar, hosting, everything.
3. **Core flows/invocations** — the 2–5 journeys or call paths. For each: input, output, what "good" looks like.
4. **Data lifetime** — does anything persist? Across devices/runs? Deleted when?
5. **External services & cost ceilings** — per-use costs (LLM calls, APIs)? "What's your monthly ceiling?" produces a real constraint.
6. **Failure behavior** — for each external dependency: when it's down, what should the consumer experience?
7. **Privacy** — does the data include anything the user wouldn't hand to a third-party API?
8. **Success metric** — "Three months from now, how do you know this was worth building?"
9. **Non-goals sweep** — at the end: "Here's what I understood is OUT of scope: ... confirm?"

## Product (humans use it)

- **Platform & context** — CLI, web, mobile-web? Where is the user physically when using it (desk, transit, offline)?
- **Auth & identity** — accounts, or local-only? (Recommend against accounts until multi-user is real.)
- **Connectivity** — must anything work offline or with flaky network?
- **Polish bar** — personal tool or something they'd show others? Drives the `/design` stage's weight.

## Infra / library (programs and developers use it)

- **The consumer** — what code calls this, written by whom? Get one concrete call-site story (the infra version of the triggering moment).
- **API surface & stability** — what's public and promised vs. internal and changeable? Smaller promise = cheaper evolution.
- **Versioning & compatibility** — what does a breaking change cost the consumers? Semver discipline needed?
- **SLOs** — latency/throughput/availability targets as numbers, not adjectives. "How slow before a consumer notices? Before they page someone?"
- **Operational model** — who runs it, who gets paged, what do they need to see (metrics/logs/dashboards) to debug at 3am?
- **Adoption/migration story** — does anything exist today that consumers must move off of? Migration is often the real project.

## Data / ML pipeline

- **Data contracts** — sources, schemas, who owns them, what happens when an upstream schema changes without warning.
- **Freshness & latency** — how stale is acceptable? Batch or streaming, and what forces that answer?
- **Quality metric** — how is output goodness measured (eval set, spot checks, downstream complaints)? What does a wrong output *cost*?
- **Drift & monitoring** — how would you notice the model/data degrading before users do?
- **Reprocessing** — when logic changes, does history get recomputed? At what scale/cost?

## Automation / script

- **Idempotency** — what happens on double-run? On a re-run after a half-finished failure?
- **Blast radius** — worst case if it runs with a bug? Does it need a `--dry-run` mode (almost always yes) and confirmation gates for destructive steps?
- **Trigger & schedule** — manual, cron, event? What if two instances run concurrently?
- **Failure notification** — who finds out it silently stopped working, and how long until they notice?

## Question craft

- **Depth-first beats breadth-first.** Resolving one topic fully produces requirements; ten half-answered topics produce assumptions.
- **Offer options when the space is enumerable** (AskUserQuestion with 2–4 options + trade-offs); **ask open when options would anchor**.
- **Probe stated requirements with consequences, not "why".** "If we cut X, what breaks?" gets better data than "why do you want X?".
- **Contradiction protocol:** restate both statements verbatim, ask which wins. Never average them.
- **Research move:** when the user says "I don't know, what's normal?" — research 2–3 real products/tools, summarize how each handles it, recommend one with reasoning. Bursts go to a subagent; cite findings; never present invented behavior as research.

## Anti-patterns (the failure modes this skill exists to prevent)

- Asking a 10-question wall the user answers shallowly.
- Writing "the user wants standard authentication" when auth was never discussed.
- Accepting "make it fast" without converting it to a number or a comparison.
- Moving to a new topic while the current one has a known contradiction.
