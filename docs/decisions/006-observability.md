# ADR-006: Observability — OTel spans + events, structured schema, agent-debuggable

Status: accepted · Date: 2026-06-12

## Context

The PRD requires that a failed itinerary build be diagnosable from telemetry alone. There's a second consumer the usual app doesn't have: this project is built by **AI subagents** whose `/build-milestone` and `/debug` loops benefit from rich traces that go beyond what unit tests reveal (bad LLM curation, a criss-crossing day, a silent fallback). What observability design serves both?

## Options considered

1. **structlog JSON logs only.** Simple, familiar.
   - Cons: no timing or causal structure; hard to see *where* time went or *why* a route turned out as it did; correlating a multi-step build is manual.
2. **OpenTelemetry spans only.** Structured, timed operations with parent/child causality.
   - Cons: awkward for point-in-time narrative ("decided to fall back to OSM", "kept 3 of 8 candidates") — that's not a span, it's an event.
3. **Spans + span-events/logs + a defined field schema, persisted to file.** Spans for operations; events/logs for narrative; one correlation id; JSON lines an agent can grep.
   - Cons: a bit more setup and discipline (events for decisions, not every line).

## Decision

**Option 3.** A dedicated `observability/` package (`logging.py`, `tracing.py`, `context.py`, `schema.py`). OTel spans wrap each use-case and each external call; **span events / log records** carry the less-structured narrative. All telemetry shares the canonical field schema (engineering-standards.md) and a per-run `correlation_id`. JSON logs go to `logs/app.jsonl` + stdout; spans to console/file (optional local Jaeger). **LLM calls** log their structured output plus a model-produced **`reasoning`** field at DEBUG. Telemetry never lives in the persistence DB. Built in M0.

## Consequences

- A failed build is diagnosable from `logs/app.jsonl` + spans without a debugger — and a **build/debug subagent can read them** to diagnose what unit tests miss: poor curation → read the logged `reasoning`; a criss-crossing day → read the span timings and routing decisions; a silent degrade → find the OSM-fallback event.
- **LLM `reasoning` serves double duty:** the user-facing "why this place" *and* a debugging signal. Asking for it also improves the model's judgment. Gated to DEBUG; never logs secrets or full prompts.
- Built once in M0, inherited by every later milestone; small upfront cost, compounding payoff.
- Span-events require discipline (use for decisions and boundaries, not narration of every line) — the standards doc states the bar.
