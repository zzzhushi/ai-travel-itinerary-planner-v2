# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A locally-run, **Gemini / multi-provider** (not Claude) AI travel itinerary planner in Python:
city + days + preferences → a day-by-day Schedule that minimises cross-city travel.

**Status: planning complete, _no application code yet_.** Build follows [docs/ROADMAP.md](docs/ROADMAP.md)
phase by phase. Start there ("First action for the next session").

## Read first — these docs are the source of truth

- [CONTEXT.md](CONTEXT.md) — domain glossary. **Use these exact terms** (Trip, Category, Interest, Option, Rating, Chosen, Capacity, Home Base, Pinned Commitment, Anchor, Schedule).
- [docs/PRD.md](docs/PRD.md) — requirements (`FR-*`/`NFR-*`), scope, Future-Requirements triage, open questions (OQ-1..9).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — package layout, interfaces, data model, data flow, config.
- [docs/adr/](docs/adr/) — decisions 0001–0007 and *why*.

## Architecture (the big picture)

- **UI-agnostic core.** All logic lives in `planner/`; adapters (Typer CLI now, FastAPI+React later) depend on the core, **never the reverse**. Effects sit behind `Protocol`s with fakes: `LLMProvider`, `GeoProvider`/`TravelProvider`, `Repository`, telemetry.
- **Pipeline** (`planner/services/*`, one step each): `trip_setup → gathering(LLM) → geocoding → rating → capacity → scheduling(LLM)+validator → render`. Each step runs inside an OTel span.
- **Scheduler = LLM, kept honest by a deterministic validator.** The LLM gets the real travel matrix + Home Base + Pinned Commitments and produces the Schedule; the validator (hours/window/meal/zig-zag/pins/anchors) is the quality contract — not the LLM. Output is non-deterministic; tests assert *properties*, not exact layouts.
- **Two stores:** SQLite = domain state; Postgres = logs/telemetry. The OTel `trace_id` **is** the request id, correlating any run to its log rows.

## Locked decisions — do not relitigate (if one changes, update its ADR + CONTEXT.md inline)

- UI-agnostic core, CLI-first, FastAPI+React later — ADR-0002
- Tiered geo: Google → OSM → Gemini-estimate, behind providers — ADR-0001
- SQLite domain state + Postgres logs — ADR-0004
- OpenTelemetry + custom Postgres exporter; `trace_id` = request id — ADR-0003
- `LLMProvider` abstraction + fallback chain (Gemini → Groq/OpenRouter → Ollama); grounding decoupled — ADR-0006
- LLM scheduler + deterministic validator — ADR-0005
- Anchors: Home Base (MVP) + Pinned Commitment (one concept for weddings/locked tickets/flights) + anchor-aware clustering — ADR-0007
- Ranking: 1–5 stars, <3 excluded, Chosen = rated ≥3; Capacity gate is advisory, never blocking — CONTEXT.md

## Conventions that keep this on track

- **Vocabulary is canonical.** Match CONTEXT.md exactly in code, prompts, and docs.
- **Core purity.** Nothing in `planner/` imports from `planner_cli/`; all I/O goes through the provider/repository Protocols.
- **TDD, offline by default.** Failing test first. The default `pytest` run hits **no network** (fakes + in-memory SQLite); live API tests are gated behind an env flag.
- **Minimise LLM calls/tokens.** Cache `(city, interest)`, batch gather per Category, and send **only Chosen Options** to geocoding/scheduling.
- **Provider-agnostic core.** The LLM is Gemini/multi-provider — never assume Gemini-only features (e.g. grounding) on the hot path; keep them behind the provider.
- **Confirm OQ defaults** (ROADMAP.md) before relying on them; OQ-1 (zig-zag threshold) is the most consequential.

## Commands (intended; wired in Phase 0, not yet present)

- Tests: `pytest`; single test: `pytest tests/unit/test_x.py::test_name`; property tests in `tests/property/`.
- Lint/format: `ruff check .` / `ruff format .`; types: `mypy planner`.
- App (CLI adapter): `planner trip new | gather | rate | capacity | schedule | show`.
