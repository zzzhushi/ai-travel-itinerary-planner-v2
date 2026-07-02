# System Design Doc

Status: draft (awaiting approval) · Date: 2026-07-02 · Companions: PRD `docs/prd.md` (the *what/why*) · API `docs/api-contract.md` · Standards `docs/engineering-standards.md` · ADRs `docs/decisions/`

**What this doc is.** The engineering solution-space record: how the system is shaped, what each part owns, the numbers it's designed for, and the reasoning behind decisions that are expensive to reverse. The PRD answers *what, for whom, why*; this answers *how, with what structure, within what envelope*. Requirements live there; contracts, topology, and budgets live here.

**Lifecycle.** Living document, Gate-1 artifact of `/milestones`. A milestone that shifts anything below updates this file **in the same PR** as the change; deviating without updating it is a sync-pause trigger (implement-task step 1). Superseded text is edited in place — git history is the archive (unlike ADRs, which are append-only and get superseded, never rewritten). Milestone-level design deltas live in each milestone issue's Design section; task-level notes in sub-issues — this doc records only what those shouldn't repeat.

## 1. Context & goals

A travel itinerary planner: the user names a city, dates, lodging, interests, and pre-booked commitments; the system proposes rated candidate places and **deterministically** routes them into a feasible day-by-day plan the user can re-rank, refine in natural language, and export. Engineering goals, in priority order: (1) the schedule engine is deterministic and testable on fixtures — the LLM never authors times; (2) infeasibility is a first-class, explained outcome, not a crash or a silent drop; (3) free-tier operation — external calls are cached, quota-guarded, and degradable; (4) every failure is diagnosable from telemetry alone, by a human or a coding agent.

The riskiest assumption — *can a deterministic heuristic route well?* — was retired first on fixtures (M1–M3); data, persistence, UI, and LLM curation accrete per `docs/roadmap.md`.

## 2. Glossary (domain language — use these words in code and docs)

| Term | Meaning |
|---|---|
| **Place / RankedPlace** | A visitable POI (coords, hours, category, closed weekdays) / that place plus the user's rating (1–5) and optional duration override |
| **Anchor** (`FixedAnchor`) | A pre-booked, fixed-time commitment (dinner reservation, timed entry). Seated at exactly its time; everything else routes around it |
| **Area cluster / walking neighborhood** | A set of places where every *pair* is ≤ `walking_neighborhood_min` apart (default 30 min ≈ 2.5 km) — complete-linkage guarantee, pure geometry, no day concept |
| **Day window** | The schedulable span of one day: `[day_start, day_end]`, narrowed by `arrival_min` (day 1) / `departure_min` (last day) |
| **Walking tolerance / cap** | User multiplier on the daily walking budget: cap = 300 min × tolerance. The cap is a *soft* trim target, not an infeasibility |
| **Meal window** | A reserved eating slot; when meal planning is on, one food place is clamped into it |
| **Unscheduled** | Places that fit no day — always returned explicitly, never silently dropped |
| **Feasibility report / pushback** | The pre-build verdict: fits/requested/over_by, anchor conflicts, closed-on-all-days, rendered suggestions. Surfaces as HTTP 409 — an outcome, not an error |
| **TSPTW** | Traveling-salesman-with-time-windows: the per-day routing problem the scheduler heuristically solves |
| **ScheduleVersion** (M4) | One routed itinerary in a trip's history (last 3 kept, revertable) |

## 3. Architecture

Layered, pure domain core (ADR-002). Dependencies point one way — inward; `domain/` imports nothing from `services/`, `application/`, or `web/`. Travel time enters the domain as an injected `Callable[[Coord, Coord], int]` (ADR-003), rounded UP to 15-min blocks (ADR-007) — the same callable that costs routes also shapes clusters, so cost and geometry never disagree.

```
cli.py ─┐                        ┌─ services/travel.py (haversine; ADR-003 swap point)
        ├──→ application/ ──→ domain/  ←── injected callables only
web/  ──┘    (use-cases,
             presenters)         observability/ — cross-cutting (spans, events, schema)
```

### Component responsibilities

| Module | Owns | May import |
|---|---|---|
| `domain/models.py` | All domain dataclasses; minutes-since-midnight time convention | nothing (stdlib only) |
| `domain/durations.py` | Category default visit durations, per-place override, food categories | models |
| `domain/budgets.py` | Day windows incl. partial first/last days | models |
| `domain/clustering.py` | Complete-linkage proximity clustering — pure geometry, no day concept | models |
| `domain/scheduler.py` | Single-day TSPTW: greedy earliest-finishing + 2-opt; anchor segment-slicing; anchor conflict detection | models, durations |
| `domain/planner.py` | Trip orchestration: cluster → assign clusters to days (k-means on centroids) → per-day schedule → meal clamping → walking-cap trim | models, budgets, clustering, durations, scheduler |
| `domain/feasibility.py` | Pre-build verdict: capacity, closed-on-all-days, anchor conflicts | models, planner, scheduler, pushback |
| `domain/pushback.py` | Suggestion-line templating for the feasibility report (no LLM, no I/O) | stdlib |
| `domain/edits.py` | Deterministic re-solve inputs: `with_swap`, `with_rating` → new Trip | models |
| `application/build_schedule.py` | The schedule use-case: wire engine + observability; default travel fn | domain, observability, services |
| `application/presenters.py` | Deterministic day-view rendering (one presenter, all trip lengths) | domain |
| `services/travel.py` | Haversine minutes (ceil-15). Swap point for a real routing API | domain models only |
| `web/`, `cli.py` | Two bindings of the same use-cases; Pydantic schemas at the HTTP boundary only | application, domain models |
| `observability/` | structlog JSON, OTel spans, correlation context, field schema | stdlib + libs |

Layering rule of thumb: if it needs `num_days`, it's planning, not geometry (planner, not clustering); if it renders text, it's presentation (pushback/presenters, not the engine); if it does I/O, it's services/delivery, never domain. *(Known violation: `pushback.py` templating sits inside `domain/` — ledgered, see debt.md.)*

### Core flows

**Build (POST /schedule → 201):** request schema → `Trip` → `check_feasibility` (may 409) → `build_schedule` (span) → `schedule_trip`: cluster places into walking neighborhoods → k-means neighborhoods onto days (anchors pin day 0 today; anchor-day grouping when anchors span days) → per day: clamp meal picks → TSPTW route (greedy + 2-opt; anchored days: slice the day at each anchor, fill segments) → trim to walking cap (rating-aware: lowest-rated dropped first, anchors never) → `Itinerary` (+ `unscheduled`) → presenter → response.

**Pushback (409):** same until `check_feasibility` fails → report with numbers (`fits`, `requested`, `over_by`), anchor conflicts, closed-all-days ids, templated suggestions → 409 body. The user re-ranks/swaps and rebuilds — the deterministic re-solve loop that M7's NL refinement will drive.

**Re-solve after edit:** `with_rating` / `with_swap` → new `Trip` → build again. Same inputs → same plan (determinism is a test invariant).

## 4. Data model

Ownership: **Trip** (dates, lodging, windows, tolerances, meal windows, anchors) → owns **RankedPlace** → wraps **Place**; **FixedAnchor** pairs a Place with a fixed arrival + duration. Engine output: **Itinerary** → **Day** → **ScheduledStop**, plus `unscheduled`. **FeasibilityReport** is derived, never stored. All frozen dataclasses; times are minutes-since-midnight ints; HH:MM only at the edges.

Lifecycle today: everything is request-scoped (fixtures in, response out — nothing persists). M4 (ADR-004): SQLite with **durable tables** (Trip, ratings, ScheduleVersion — last 3, revertable) separated from a **TTL place-cache** (re-fetchable external data; TTL-stale data is re-hydrated on read, visibly). Schema ownership: repository layer, arriving M4; domain stays persistence-ignorant.

## 5. Interface contracts

`docs/api-contract.md` is the contract: **use-cases = API**, CLI and web are two bindings of the same 12 operations. Error semantics that shape the design: **409 = infeasible with numbers** (first-class outcome); **422** = semantically invalid input; **429** = QuotaGuard refused before billing; **424/502 → 200 + `outcome: degraded`** when a fallback succeeded. Degradation is visible, never silent.

## 6. Key decisions

| Decision | Rejected alternative | ADR |
|---|---|---|
| Structured place-data API as source of truth; LLM curates, never authors facts | LLM-generated place data | [001](decisions/001-place-data-source.md) |
| Layered architecture, pure domain core | Hexagonal ports-and-adapters ceremony | [002](decisions/002-application-architecture.md) |
| Custom heuristic scheduler first; OR-Tools as contained swap behind the same interface | Solver dependency up front | [003](decisions/003-scheduler-heuristic.md) |
| SQLite; TTL place-cache separate from durable tables | Postgres / flat files | [004](decisions/004-persistence-sqlite-cache.md) |
| FastAPI + Jinja2/htmx + Leaflet | React SPA | [005](decisions/005-web-delivery.md) |
| OTel spans + structured schema, agent-debuggable | ad-hoc logging | [006](decisions/006-observability.md) |
| Travel times rounded UP to 15-min blocks (realistic buffers, coarse-grained determinism) | exact haversine minutes | [007](decisions/007-travel-time-rounding.md) |

## 7. External dependencies & degradation

The product engine currently has **zero live external dependencies** (fixtures only). Planned, with contracted failure behavior:

| Dependency | Arrives | Role | When it's down / limited |
|---|---|---|---|
| Google Places (New) | M5 | place facts source of truth | → OSM fallback, response `outcome: degraded`; both down → 503 |
| OSM/Overpass | M5 | fallback place source | per-place `hours_unverified` flag |
| Gemini (LLM) | M6–M7 | interest→query, fit-filter, refinement *sketches* — never schedule times | curation skipped/cached + visible banner; engine still routes |
| QuotaGuard (internal) | M5 | refuse before free-tier billing | 429 with reset info — a feature, not a failure |
| Ollama (dev tooling) | now | local-LLM task executor for the *build process*, not the product | cloud-tier subagent fallback; no product impact |

## 8. Cross-cutting concerns

- **Error taxonomy:** user-fixable infeasibility → 409 report; invalid input → 422; internal invariant violations → `raise RuntimeError` with a diagnostic (never `assert` — `-O` strips it); places that don't fit → `unscheduled`, never dropped. Retries (tenacity, backoff+jitter) only at external-call boundaries — never around internal logic.
- **Observability:** every use-case and external call in a span with `duration_ms`/`outcome`; `correlation_id` on every line; field schema in `docs/engineering-standards.md`. Logs serve two readers: a human, and a coding agent debugging its own output (`/debug`, `/build-milestone` read them).
- **Security & privacy:** no secrets/keys/full prompts in logs; gitleaks pre-commit; `.env` read-only; place queries are the only user data leaving the machine (M5+), and only to the chosen place API.
- **Performance envelope (designed-for numbers, not aspirations):** ≤ ~50 candidate places per trip, ≤ ~15 per day, ≤ 14 days; `POST /schedule` p95 < 2 s at that scale. Known super-linear spots are deliberate at this scale and ledgered with promotion triggers in `docs/debt.md` (walking-cap trim O(N²) schedules/day; feasibility double-build; naive complete-linkage O(N³)). The envelope is re-negotiated here, in a PR, when M5 real data changes N.

## 9. Testing strategy

Exit-criteria tests are written and committed **before** feature code each milestone and are immutable without user approval — they are the spec. Engine tests are deterministic and fixture-built: travel time is an injected grid function so assertions are exact; no network anywhere in the suite. Every public function/endpoint gets happy-path + failure-path; bug fixes land with a regression test that fails on the old code. Coverage floor 70% (CI-gated) — a consequence of pinning behavior, never a target. Verify line (single source: CLAUDE.md § Conventions): `uv run ruff check && uv run mypy && uv run pytest -q`.

## 10. Risks & mitigations

- ~~Heuristic can't route well~~ — retired M1–M3 (exit criteria green on fixtures).
- **Free-tier quota blowout at real data (M5)** — QuotaGuard refuses before billing; TTL cache; OSM fallback with visible degradation.
- **LLM curation quality (M6)** — curation is advisory over structured facts (ADR-001); `reasoning` exposed per suggestion; deterministic engine unaffected by LLM failure.
- **Anchors are single-day (M3 scope)** — multi-day trips seat anchors on day 0 only; anchor-day grouping (anchors define day structure; k-means becomes the unanchored fallback) is designed but unbuilt. Revisit at M4/M7.
- **SQLite migration (M4)** — first durable state; schema changes after M4 need a migration story before, not after, real trips exist.

## 11. Open questions

- `PUT /trips/{id}/ratings` — deferred to M4 (needs a Trip that outlives one request).
- `FixedAnchor` carries no date — decide when multi-day anchor trips become real (M7 at the latest).
- Should the 409 gate fire on feasible-but-cap-trimmed trips (walking cap is a soft preference)? Currently it does; contract decision pending user review of PR #33 findings.
- OR-Tools swap trigger — define the quality/scale threshold that would justify it (ADR-003 left it open).
