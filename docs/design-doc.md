# System Design Doc

Status: draft (awaiting approval) · Date: 2026-07-02 · Owner artifacts: PRD `docs/prd.md` · API `docs/api-contract.md` · Standards `docs/engineering-standards.md` · ADRs `docs/decisions/`

Living document: the Gate-1 output of `/milestones`. A milestone that shifts anything below updates this file in the same PR; deviating from it without updating it is a sync-pause trigger (implement-task step 1). Milestone-level design lives in each milestone issue's Design section; task-level design notes live in sub-issues — this doc records only what those shouldn't repeat.

## Context & goals

A travel itinerary planner: the user names a city, dates, lodging, interests and pre-booked commitments; the system proposes rated candidate places and deterministically routes them into a feasible day-by-day plan the user can re-rank, refine in natural language, and export. The riskiest assumption — "can a deterministic heuristic route well?" — was retired first on fixtures (M1–M3); data, persistence, UI, and LLM curation accrete per `docs/roadmap.md`.

## Architecture

Layered, with a pure domain core (ADR-002). Dependency direction is one-way, inward:

```
cli.py ─┐                      ┌─ services/travel.py (haversine)
        ├─→ application/ ─→ domain/ ←─ injected callables only
web/  ──┘   (use-cases,        (models, clustering, scheduler,
            presenters)         planner, feasibility, edits,
                                durations, budgets)
observability/ — cross-cutting (spans, events, structured schema)
```

- `domain/` imports nothing from `services/`, `application/`, or `web/`. Travel time enters as an injected `Callable[[Coord, Coord], int]` (ADR-003), rounded up to 15-min blocks (ADR-007) — the same callable that costs routes also shapes clusters.
- `application/` wires use-cases with observability; one use-case = one operation in `docs/api-contract.md`.
- Two delivery surfaces, one contract: CLI (fixtures-first, ships each operation before the web) and FastAPI + Jinja2/htmx + Leaflet (ADR-005) binding the same use-cases.
- Scheduling pipeline inside `domain/`: proximity clustering (complete-linkage, pure geometry) → day assignment (k-means on cluster centroids; anchor-driven once anchors span days) → per-day TSPTW (greedy earliest-finishing + 2-opt; anchored days use time-window segment slicing) → walking-cap trim (rating-aware).

## Data model

Entities and ownership (not a schema): **Trip** (dates, lodging, day window, tolerances, meal windows, anchors) owns **RankedPlace** (rating 1–5, duration override) wrapping **Place** (coords, hours, closed weekdays) and **FixedAnchor** (place + fixed arrival + duration). The engine returns **Itinerary** → **Day** → **ScheduledStop**, plus `unscheduled` (never silently dropped). **FeasibilityReport** is the pre-build verdict (fits/requested/over_by, anchor conflicts, closed-all-days, suggestions). Planned M4: **ScheduleVersion** (last 3 kept, revertable) and SQLite persistence with a TTL place-cache separate from durable tables (ADR-004). **Interest**/**Suggestion** arrive with real place data (M5) and LLM curation (M6).

Times are minutes-since-midnight ints throughout the domain; rendered to HH:MM only at the edges.

## Interface contracts

`docs/api-contract.md` is the operation contract (use-cases = API; CLI and web are two bindings). Error semantics that shape the design: **409 is a first-class outcome, not an error** — the deterministic feasibility check returns pushback numbers and both surfaces render them; degradation is visible (`outcome: degraded`, `hours_unverified`) rather than silent fallback.

## Key decisions

| Decision | Rejected alternative | ADR |
|---|---|---|
| Structured place-data API (Google Places New) as source of truth; LLM curates | LLM-generated place facts | [001](decisions/001-place-data-source.md) |
| Layered architecture, pure domain core | Hexagonal/ports-and-adapters ceremony | [002](decisions/002-application-architecture.md) |
| Custom heuristic scheduler first; OR-Tools as contained swap | Solver dependency up front | [003](decisions/003-scheduler-heuristic.md) |
| SQLite, TTL place-cache separate from durable tables | Postgres / files | [004](decisions/004-persistence-sqlite-cache.md) |
| FastAPI + Jinja2/htmx + Leaflet | React SPA | [005](decisions/005-web-delivery.md) |
| OTel spans + structured schema, agent-debuggable | ad-hoc logging | [006](decisions/006-observability.md) |
| Travel times rounded UP to 15-min blocks | exact haversine minutes | [007](decisions/007-travel-time-rounding.md) |

## Cross-cutting concerns

- **Errors:** places that don't fit land in `unscheduled`; infeasibility is a 409 with numbers; internal invariant violations raise (never assert — `-O` strips it). Retries (tenacity) only at external-call boundaries.
- **Observability:** every use-case and external call wrapped in a span with `duration_ms`/`outcome`; standard field schema in `docs/engineering-standards.md`; logs serve a human AND a coding agent debugging its own output.
- **Security/privacy:** no secrets/keys/full prompts in logs; gitleaks pre-commit; `.env` read-only.
- **Performance budget:** fixtures-scale today (≤~50 places, ≤~15/day) — O(N²) spots are ledgered in `docs/debt.md` with promotion triggers, not pre-optimized.

## Risks & mitigations

- ~~Heuristic can't route well~~ — retired M1–M3 (exit-criteria tests green on fixtures).
- **Free-tier quota blowout at real data (M5)** — QuotaGuard refuses before billing (429); TTL cache; OSM fallback with visible degradation.
- **LLM curation quality (M6)** — curation is advisory over structured data (ADR-001); `reasoning` field exposed for judgment.
- **Anchors are single-day (M3 scope)** — multi-day trips seat anchors on day 0 only; anchor-driven day assignment is designed (clusters group by anchor day; k-means becomes the unanchored fallback) but not built. Revisit at M4/M7.

## Open questions

- `PUT /ratings` persistence — deferred to M4 (needs a Trip that outlives one request).
- Anchor dates (`FixedAnchor` carries no date) — decide when multi-day anchor trips become real (M7 refinement at the latest).
- Whether the 409 gate should also fire on walking-cap-trimmed (feasible-but-partial) trips — currently it does; contract decision pending user review of PR #33 findings.
