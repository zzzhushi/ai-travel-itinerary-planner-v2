# Interview guide — topic checklist and question craft

## Topic checklist (raise the relevant ones as questions, with a recommendation)

Work these in rough priority order; skip ones that obviously don't apply, but say you're skipping them and why.

1. **The triggering moment** — "Walk me through the last time you actually needed this. What did you do instead?" (Grounds everything in a real scenario; kills imagined requirements.)
2. **Audience** — just the user, or others? Changes auth, polish bar, hosting, everything.
3. **Core flows** — the 2–5 journeys. For each: input, output, what "good" looks like.
4. **Data lifetime** — does anything persist? Across devices? Deleted when?
5. **Auth & identity** — accounts? Or local-only? (Most solo tools don't need accounts in v1 — recommend against until multi-user is real.)
6. **External services & cost ceilings** — LLM calls cost money per use. "What's your monthly ceiling?" produces a real constraint.
7. **Failure behavior** — for each external dependency: when it's down, what should the user see?
8. **Offline / connectivity** — matters for travel apps specifically; ask, don't assume.
9. **Privacy** — does the data include anything the user wouldn't paste into a third-party API?
10. **Platform** — CLI, web, mobile-web? Where will the user actually be when using it?
11. **Success metric** — "Three months from now, how do you know this was worth building?"
12. **Non-goals sweep** — at the end: "Here's what I understood is OUT of scope: ... confirm?"

## Question craft

- **Depth-first beats breadth-first.** Resolving one topic fully produces requirements; ten half-answered topics produce assumptions.
- **Offer options when the space is enumerable** (AskUserQuestion with 2–4 options + trade-offs); **ask open when options would anchor** ("what's the worst itinerary an app ever gave you?").
- **Probe stated requirements with consequences, not "why".** "If we cut X, what breaks?" gets better data than "why do you want X?".
- **Contradiction protocol:** restate both statements verbatim, ask which wins. Never average them.
- **Research move:** when the user says "I don't know, what's normal?" — WebSearch 2–3 real products, summarize how each handles it, recommend one with reasoning. Cite what you found; never present invented behavior as research.

## Anti-patterns (these are the failure modes this skill exists to prevent)

- Asking a 10-question wall the user answers shallowly.
- Writing "the user wants standard authentication" when auth was never discussed.
- Accepting "make it fast" without converting it to a number or a comparison.
- Moving to a new topic while the current one has a known contradiction.
