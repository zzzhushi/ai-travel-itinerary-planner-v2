# PRD — AI Travel Itinerary Planner

**Status:** Draft
**Author:** zzzhushi
**Date Created:** 2026-06-09
**Last Updated:** 2026-06-09
**Version:** 1.0

> Companion docs: domain glossary in [CONTEXT.md](../CONTEXT.md); architecture in
> [ARCHITECTURE.md](./ARCHITECTURE.md); decisions in [docs/adr/](./adr/). Terms in
> **Title Case** (Trip, Category, Interest, Option, Rating, Chosen, Capacity, Schedule)
> are defined in CONTEXT.md.

---

## Executive Summary

**One-liner:** A locally-run, LLM-powered planner that turns a city + trip length +
preferences into a day-by-day Schedule that minimises back-and-forth travel.

**Overview:** Travellers arriving in an unfamiliar city struggle to turn a vague list of
interests ("ramen, museums, jazz") into a realistic daily plan that doesn't waste hours
zig-zagging across town. This tool collects the traveller's Interests under chosen
Categories, uses an LLM to propose concrete, real Options for each, lets the traveller
rate them, then generates a travel-aware Schedule across the trip's days. It runs locally
in Python, is resumable across sessions, and is instrumented for diagnostics.

**Quick Facts:**
- **Target User:** an individual traveller planning their own trip; also the author, as a
  learning vehicle for FastAPI/React, PostgreSQL, and OpenTelemetry.
- **Problem Solved:** converting loose interests into a feasible, low-travel daily plan.
- **Key Metric (North Star):** Schedules accepted without manual reordering.
- **Target:** working CLI engine first; FastAPI+React UI later.

---

## Problem Statement

### The Problem
Planning a multi-day trip means juggling many candidate places against opening hours,
meal times, and — hardest of all — geography. Done by hand or with a generic chatbot, the
result either ignores travel time (sending you across the city and back) or can't be
trusted (hallucinated or closed venues).

### Current State
Travellers stitch together blogs, Google Maps lists, and chatbot answers manually. LLM
chatbots will happily produce a day plan but routinely (a) invent or misplace venues and
(b) ignore travel cost, producing inefficient routes with no way to verify quality.

### Impact
- **User:** hours of manual research and re-ordering; trips with avoidable backtracking.
- **Author/business:** none directly (personal project); value is the working tool plus
  demonstrable skills (full-stack, observability, LLM integration).

### Why Now?
Free-tier LLMs with grounding and structured output are good enough to draft real Options
cheaply, and the geographic reasoning they're *bad* at is exactly what a small deterministic
layer can supply.

---

## Goals & Objectives

### User Goals
1. Go from interests → a concrete shortlist of real places to research.
2. Express preferences (categories, pace, ratings) and have them honoured.
3. Get a day-by-day Schedule that minimises travel and respects opening/meal times.
4. Resume planning across sessions without losing state.

### Project Goals
1. Prove the hard parts (grounded Option gathering, travel-aware scheduling) on a CLI.
2. Keep LLM token/call usage low enough to live within free tiers.
3. Be observable and testable end-to-end.
4. Build toward a FastAPI+React UI for portfolio/skills value.

### Non-Goals
- Booking, payments, or reservations.
- Multi-traveller collaboration or accounts (single local user for now).
- Real-time re-routing during the trip.
- Flights/inter-city travel — the Schedule starts when the traveller lands.

---

## User Personas

### Primary Persona: The self-planning traveller
- **Tech savviness:** Medium–High (comfortable running a CLI, editing a `.env`).
- **Behaviours:** researches trips in advance; keeps lists of places; values efficient days.
- **Needs:** real, current places; a plan that respects geography and hours; control over
  what's included.
- **Pain points:** generic plans ignore travel time; chatbots suggest closed/fake venues;
  re-ordering a day by hand is tedious.
- **Quote:** _"Just give me a route that doesn't make me cross the city four times."_

---

## User Stories & Requirements

### Epic A — Trip setup

##### Story A1: Create a Trip
```
As a traveller,
I want to set up a Trip with city, arrival time, number of days, and preferences,
So that the planner knows the constraints to plan within.
```
**Acceptance Criteria:**
- [ ] Given a city, `arrival_at`, `num_days`, pace, daily window, and transport mode, when I
      create a Trip, then it is persisted and resumable by id.
- [ ] The planner offers common default Categories which I can accept, edit, or extend.
- [ ] Day 1 is anchored at `arrival_at` (a late arrival yields fewer Day-1 slots).
**Priority:** P0 · **Effort:** M

##### Story A2: Add Interests under Categories
```
As a traveller,
I want to type specific Interests under each Category,
So that the planner searches for the right kinds of places.
```
**Acceptance Criteria:**
- [ ] I can add one or more Interests (free text) under any Category.
- [ ] An empty Category (no Interests) is allowed but flagged as a coverage gap.
**Priority:** P0 · **Effort:** S

##### Story A3: Set a Home Base
```
As a traveller,
I want to set my lodging as the trip's Home Base,
So that each day's plan starts and ends where I'm staying.
```
**Acceptance Criteria:**
- [ ] I can provide a lodging name/address; it is geocoded via the tier ladder (ADR-0001).
- [ ] Every day's Schedule starts and ends at Home Base, and travel to/from it is counted.
- [ ] One Home Base per Trip (multiple/changing lodgings are out of scope for now).
**Priority:** P0 · **Effort:** M · **Ref:** [ADR-0007](./adr/0007-anchors-and-anchor-aware-scheduling.md)

### Epic B — Option gathering

##### Story B1: Gather Options for Interests
```
As a traveller,
I want the planner to propose concrete, real Options for each Interest,
So that I have specific places to research and rate.
```
**Acceptance Criteria:**
- [ ] Given a Trip with Interests, when I run gather, then each Interest receives N concrete
      Options with name, description, address, and an estimated location.
- [ ] Options are grounded in real/current places when grounding is available (see ADR-0006).
- [ ] Re-running gather for an unchanged `(city, Interest)` uses cache and makes no new LLM call.
- [ ] Near-duplicate Options across Interests are de-duplicated by place/coordinates.
**Priority:** P0 · **Effort:** L · **Depends:** A2, [ADR-0006](./adr/0006-llm-provider-abstraction-fallback-chain.md)

##### Story B2: Resolve geography for Options
```
As the system,
I want each Option to have verified coordinates and pairwise travel times,
So that the scheduler can minimise travel.
```
**Acceptance Criteria:**
- [ ] Each Option is geocoded via the tier ladder Google → OSM → LLM-estimate; `geo_source`
      records which tier answered ([ADR-0001](./adr/0001-tiered-geo-sourcing.md)).
- [ ] A travel-time matrix is computed for the Chosen set for the Trip's transport mode.
**Priority:** P0 · **Effort:** L · **Depends:** B1

### Epic C — Rating & the Capacity gate

##### Story C1: Rate Options
```
As a traveller,
I want to rate each Option 1–5 stars,
So that the planner prioritises what I care about and excludes what I don't.
```
**Acceptance Criteria:**
- [ ] I can assign a 1–5 Rating to any Option; ratings below 3 exclude it from scheduling.
- [ ] The Chosen set is exactly the Options rated ≥ 3.
- [ ] Unrated Options are treated as excluded.
**Priority:** P0 · **Effort:** S · **Depends:** B1

##### Story C2: "Enough options" guidance
```
As a traveller,
I want to know whether I have enough Chosen Options for my trip length,
So that I can gather more or proceed knowingly.
```
**Acceptance Criteria:**
- [ ] Capacity = days × slots-per-day (from pace), minus Day-1 reduction from `arrival_at`.
- [ ] Oversupply (Chosen > Capacity): the gate warns and reports how many will be trimmed.
- [ ] Undersupply (Chosen < Capacity): the gate warns and suggests gathering more.
- [ ] The gate is advisory and never blocks schedule generation.
**Priority:** P1 · **Effort:** M · **Depends:** C1

### Epic D — Scheduling

##### Story D1: Generate a travel-aware Schedule
```
As a traveller,
I want a day-by-day Schedule built from my Chosen Options,
So that I have an efficient plan that respects my preferences.
```
**Acceptance Criteria:**
- [ ] Given Chosen Options + travel matrix + constraints, when I generate, then a Schedule
      with day/order/time per Option is produced and persisted.
- [ ] Higher-rated Options are prioritised; the highest are force-included on oversupply
      ([ADR-0005](./adr/0005-deterministic-travel-aware-scheduler.md)).
- [ ] Food Options are placed in meal-time windows; nothing is scheduled outside the daily
      window or an Option's opening hours.
- [ ] Each scheduled Option records `travel_minutes_from_prev`.
**Priority:** P0 · **Effort:** XL · **Depends:** B2, C1

##### Story D2: Validate the Schedule
```
As the system,
I want to score every generated Schedule deterministically,
So that quality is enforced regardless of which LLM produced it.
```
**Acceptance Criteria:**
- [ ] The validator detects opening-hours violations, daily-window overflow, meal-slot
      misfit, and per-day travel exceeding a threshold (zig-zag).
- [ ] A Schedule that fails hard checks triggers a re-prompt, capped at a max attempt count.
- [ ] An infeasible constraint (e.g. a Must-do open only on a day not in the Trip) is
      surfaced as a clear, actionable error rather than a silent drop.
**Priority:** P0 · **Effort:** L · **Depends:** D1

##### Story D3: View the Schedule
```
As a traveller,
I want to see my Schedule day by day with travel times,
So that I can follow or adjust it.
```
**Acceptance Criteria:**
- [ ] The Schedule renders per day in order, showing times, Options, and travel between them.
- [ ] An optional natural-language day summary can be generated (one extra LLM call).
**Priority:** P1 · **Effort:** M · **Depends:** D1

### Epic E — Platform (cross-cutting)

##### Story E1: Resume across sessions
```
As a traveller,
I want my Trip state saved locally,
So that I can gather, rate, and schedule across separate sittings.
```
**Acceptance Criteria:**
- [ ] All Trip state persists in local SQLite and is reloadable by Trip id between commands.
**Priority:** P0 · **Effort:** M

##### Story E2: Diagnose any run
```
As the developer,
I want every operation traced and logged with a request id,
So that I can debug behaviour and track token usage.
```
**Acceptance Criteria:**
- [ ] Every top-level command opens an OTel trace; its `trace_id` is the request id.
- [ ] Logs and per-call token counts land in Postgres, queryable by `trace_id`/`trip_id`
      ([ADR-0003](./adr/0003-otel-with-postgres-exporter.md)).
- [ ] The request id is shown to the user so they can correlate a run to its logs.
**Priority:** P0 · **Effort:** M

##### Story E3: Survive free-tier limits
```
As a traveller on free LLM tiers,
I want the planner to fall back to another provider when one is exhausted,
So that planning doesn't stop.
```
**Acceptance Criteria:**
- [ ] A quota/rate-limit error from one provider transparently falls back to the next in the
      configured chain ([ADR-0006](./adr/0006-llm-provider-abstraction-fallback-chain.md)).
- [ ] Local Ollama is usable as a last-resort provider with no API key.
**Priority:** P1 · **Effort:** M

### Functional Requirements

| Req ID | Description | Priority |
|--------|-------------|----------|
| FR-001 | Create/persist/resume a Trip with city, arrival_at, num_days, pace, daily window, transport mode | Must |
| FR-002 | Offer default Categories; allow add/edit; add free-text Interests under Categories | Must |
| FR-003 | Gather N concrete Options per Interest via an LLMProvider, grounded when available | Must |
| FR-004 | Return Options as structured records (name, desc, address, coords, hours, est. visit minutes) with defensive parsing | Must |
| FR-005 | Cache gathered Options by `(city, interest)`; avoid repeat LLM calls | Must |
| FR-006 | De-duplicate near-identical Options by place/coordinates | Should |
| FR-007 | Geocode each Option via Google → OSM → LLM-estimate; record `geo_source` | Must |
| FR-008 | Compute a pairwise travel-time matrix for Chosen Options per transport mode | Must |
| FR-009 | Capture 1–5 Rating per Option; exclude < 3; Chosen = rated ≥ 3 | Must |
| FR-010 | Compute Capacity; warn on over/undersupply; never block scheduling | Should |
| FR-011 | Generate a Schedule from Chosen + matrix + constraints via an LLMProvider | Must |
| FR-012 | Enforce opening hours, daily window, meal slots, Day-1 arrival, pace caps as hard constraints | Must |
| FR-013 | Validate every Schedule (hours/window/meal/zig-zag); re-prompt on failure up to a cap | Must |
| FR-014 | Surface infeasible constraints as actionable errors | Should |
| FR-015 | Persist Schedule with per-Option times and `travel_minutes_from_prev` | Must |
| FR-016 | Render Schedule per day with travel times; optional LLM prose summary | Should |
| FR-017 | Trace every command (trace_id = request id); persist logs + token counts to Postgres | Must |
| FR-018 | Fall back across LLM providers on quota errors; support local Ollama | Should |
| FR-019 | Anchor each day at a geocoded Home Base; count travel to/from it | Must |
| FR-020 | Accept the scheduler's input contract for Pinned Commitments (fixed time+place, immovable on regen) even if the add-pin UI lands later | Should |

### Non-Functional Requirements

| Req ID | Category | Requirement | Target |
|--------|----------|-------------|--------|
| NFR-001 | Runs locally | Plan a Trip end-to-end with only SQLite present | No paid service required |
| NFR-002 | Cost | Minimise LLM calls/tokens | Cached `(city, interest)` ⇒ 0 new calls; ~1 gather call per Category |
| NFR-003 | Testability | Default test run hits no external API | Fakes for LLM + geo; deterministic |
| NFR-004 | Quality | Validator invariants always hold on emitted Schedules | 0 hours/window violations in property tests |
| NFR-005 | Portability | Core is model-agnostic | No provider-specific assumptions on the hot path |
| NFR-006 | Observability | Any run correlatable from request id to logs | 100% of commands traced |
| NFR-007 | Reproducibility | Domain logic deterministic; scheduling validated not asserted-exact | Property-based tests on validator |

> **Ambiguity flags (per skill guardrail — needs a concrete, testable threshold before build):**
> - NFR-004 "per-day travel exceeding a threshold (zig-zag)" — define the threshold (e.g.
>   minutes/day, or % over the optimal nearest-neighbour route). **Open Question OQ-1.**
> - FR-003 "N Options per Interest" — fix a default N. **Open Question OQ-2.**

---

## Success Metrics

No revenue/acquisition funnel (personal tool), so a **custom framework** focused on task
success and cost:

**North Star:** % of generated Schedules the user accepts **without manual reordering**.

| Metric | Definition | Target |
|--------|------------|--------|
| Schedule acceptance | Schedules used as-is vs regenerated/edited | Trend up |
| Avg travel minutes/day | Mean intra-day travel in emitted Schedules | Below the zig-zag threshold (OQ-1) |
| LLM calls per completed Trip | Total provider calls from setup → Schedule | Minimised; cache hit-rate tracked |
| Validator pass rate (pre-reprompt) | Schedules passing hard checks on first try | Trend up as prompts improve |
| Test suite runtime | Full default suite wall-clock | Fast enough to run on every change |
| Grounding rate | % Options that geocoded via Google/OSM (not LLM-estimate) | Higher = more real places |

**Events to track (via the telemetry layer):** `trip_created`, `options_gathered`
(with cache_hit, provider, tokens), `options_rated`, `capacity_checked`,
`schedule_generated` (with validator score, reprompts), `schedule_viewed`.

---

## Scope

### In Scope — Phase 1 (CLI MVP)
- Trip setup, Interests, default Categories, **Home Base anchoring each day** (ADR-0007).
- **Pinned Commitment seam** in the scheduler contract (full add-pin UX may follow).
- LLM Option gathering (grounded, structured, per-Category batched, cached) via LLMProvider.
- Tiered geocoding + travel matrix.
- 1–5 Rating, Chosen set, Capacity gate.
- LLM scheduling + deterministic validator + capped re-prompt.
- Schedule rendering in the CLI.
- SQLite persistence; OTel + Postgres logging; provider fallback chain.

### In Scope — Phase 2 (later)
- FastAPI API over the core; `X-Request-ID` response header.
- React frontend (ranking UI, Schedule/map visualisation).
- Optional pluggable SearchProvider so non-grounding models get real places.

### Out of Scope
- Booking/payments/reservations; flights/inter-city legs.
- Accounts, multi-user, sharing.
- Mobile apps; offline maps.
- In-trip live re-routing.

### Future Considerations
- Swap the scheduler/LLM behind their interfaces (e.g. OR-Tools, upgraded models).
- Migrate domain state SQLite → Postgres when multi-user.
- Multi-city / multi-leg trips.

---

## Technical Considerations

High-level architecture, the package layout, and the key interfaces live in
[ARCHITECTURE.md](./ARCHITECTURE.md). Decisions and their rationale are in
[docs/adr/](./adr/). Summary:

- **Shape:** UI-agnostic `planner` core; Typer CLI now, FastAPI+React later ([ADR-0002](./adr/0002-ui-agnostic-core-cli-first.md)).
- **LLM:** `LLMProvider` interface + fallback chain (Gemini → Groq/OpenRouter → Ollama); grounding decoupled ([ADR-0006](./adr/0006-llm-provider-abstraction-fallback-chain.md)).
- **Geo:** tiered `GeoProvider`/`TravelProvider` (Google → OSM → LLM-estimate) ([ADR-0001](./adr/0001-tiered-geo-sourcing.md)).
- **Scheduling:** LLM + travel matrix + deterministic validator ([ADR-0005](./adr/0005-deterministic-travel-aware-scheduler.md)).
- **State:** SQLite behind a repository interface ([ADR-0004](./adr/0004-sqlite-state-postgres-logs.md)).
- **Telemetry:** OpenTelemetry SDK + custom Postgres exporter; `trace_id` = request id ([ADR-0003](./adr/0003-otel-with-postgres-exporter.md)).
- **External APIs:** Gemini/Groq/OpenRouter (LLM), Ollama (local), Google Maps (Places + Distance Matrix), Nominatim/OSRM (OSM).
- **Secrets:** API keys + `POSTGRES_DSN` + provider chain via `.env` / pydantic-settings; keys never logged.

---

## Risks & Mitigation

| Risk | Impact | Prob. | Mitigation |
|------|--------|-------|------------|
| Free-tier LLM exhaustion mid-plan | High | High | Provider fallback chain + Ollama; aggressive caching; batch per Category (ADR-0006) |
| Grounding+strict-schema incompatibility in one call | Med | Med | Request JSON in-prompt + defensive parse + repair retry; verify against current docs |
| LLM produces zig-zag / infeasible Schedule | High | Med | Deterministic validator + capped re-prompt; feed real travel matrix (ADR-0005) |
| Hallucinated/closed venues | Med | Med | Grounded gather; geocoding reality-check; `geo_source` visibility |
| Geo provider rate limits (Nominatim etiquette) | Med | Med | Cache geocoding; respect usage policy; fall back tiers |
| Weak local model quality | Med | Med | Use large hosted free models for scheduling; validator catches bad output |
| Scope creep into booking/web too early | Med | Med | Phase gating; CLI must work before UI |

---

## Dependencies & Assumptions

**Dependencies:** Python toolchain; an LLM provider key (or local Ollama); optionally a
Google Maps key; a reachable Postgres for telemetry; OSM services (Nominatim/OSRM) for the
free geo tier.

**Assumptions:**
- Single local user; no auth needed in Phase 1.
- Trip starts on arrival; no flight planning.
- The traveller can run a CLI and populate a `.env`.
- Free-tier limits are workable *given* caching + batching + fallback.

---

## Open Questions

- [ ] **OQ-1 — Zig-zag threshold.** How is "too much travel" defined for the validator and
      metrics? Options: absolute minutes/day cap; % over nearest-neighbour optimal; per-day
      budget scaled by pace. *Needed before D2.*
- [ ] **OQ-2 — Options per Interest (N).** Default count to gather. Trade-off: more choice vs
      tokens. *Needed before B1.*
- [ ] **OQ-3 — Default slots-per-day per pace.** Confirm relaxed/balanced/packed → slot counts
      and meal-slot handling. *Needed before C2/D1.*
- [ ] **OQ-4 — Re-prompt cap.** Max scheduler re-prompts before surfacing best-effort + warning.
      *Needed before D2.*
- [ ] **OQ-5 — Force-include tier.** Does Rating 5 mean "must-do / force-include even at travel
      cost", or is force-include a separate flag? *Needed before D1.*

---

## Future Requirements & Triage

Captured 2026-06-09 from a feasibility pass over a wishlist. Legend — **MVP:** now;
**Next:** high-priority post-MVP; **P2:** with the web UI; **Deferred:** later, seam noted;
**Done:** already in the design.

| # | Request | Status | Disposition |
|---|---------|--------|-------------|
| 1 | Add a custom place (user Option) | Next | `Option.source="user"`; geocoding resolves the Maps link/`place_id` |
| 1 | Wedding / fixed event | Next | → Pinned Commitment ([ADR-0007](./adr/0007-anchors-and-anchor-aware-scheduling.md)) |
| 1 | Extra buffer | Next | Deterministic scheduling param (config + validator), **not** LLM-invented |
| 1a | Delete a schedule item | P2 | Schedule edit op; clarify "remove from Schedule" vs "reject Option" (rating<3) |
| 2 | Per-Option duration | Next | Already modeled (`est_visit_minutes`); precedence **user > LLM-per-option > category default**; grounded LLM can set wait-time-aware durations |
| 3 | Images | P2 | ⚠️ Google photos are **not** free permanent CDN links (key + licensing); store a photo reference rendered via API, or use Wikimedia for free landmark images. `Option.image_ref` |
| 4 | Map in the UI (options by category, schedule by day) | P2 | Pure frontend (Leaflet/Mapbox); coords/category/day already exist |
| 5 | Lock items | Next | → Pinned Commitment; regen must not move them; validator asserts it (ADR-0007) |
| 6 | Travel time + transport mode | Done / refine | `transport_mode` + travel matrix already in design; per-leg/mixed-mode is a future refinement |
| 7 | Hotels | MVP | → Home Base daily anchor (ADR-0007) |
| 7 | Flights | Deferred | A Pinned Commitment + airport↔Home Base transfer; full transfers + mid-trip flights deferred with multi-city |
| 8 | Multi-city | Deferred | Reshapes `Trip` → list of `CityStay` (city + dates + Home Base) joined by inter-city transport; today's Trip ≈ tomorrow's CityStay |
| 9 | Multiple trips | Next (small) | Each Trip already independent by id; add `trip list` + selection |
| 10 | Non-technical user / low setup / cross-platform | Deferred (goal) | ⚠️ A CLI with `.env`+keys is not non-technical; the real surface is the web UI + an `init` wizard + default local Ollama + per-OS docs. SQLite is already serverless ("just a file") so **JSON storage is unnecessary** (available behind the `Repository` interface if wanted). Cross-platform via `pathlib` + per-OS install docs |

**Decisions taken (this pass):** Pinned Commitment is one unifying concept for wedding/locked
tickets/flights; Home Base enters the MVP and anchors every day; the scheduler is
**anchor-aware** (clusters nearby Options around fixed points); the non-technical-user work is
documented as a goal but deferred.

### Travel-agent feature ideas (suggested, not yet committed)
- **Budget awareness** — rough cost per Option/day + a trip cap.
- **Weather-aware swaps** — rainy day pushes outdoor Options out, pulls indoor in.
- **Reservation flags + lead time** — "needs booking N days out."
- **Export** — `.ics` / Google Calendar / PDF: the artifact a traveller actually carries.
- **Backup/standby alternatives** — nearby same-category fallback when a place is closed.
- **Accessibility / companion pacing** — kids/elderly → fewer slots, shorter walks, low-walk days.

### New open questions from this pass
- [ ] **OQ-6 — Buffer model.** Global buffer between activities, per-Option, or per-pace? Default value?
- [ ] **OQ-7 — Pin time semantics.** Does a Pinned Commitment have a fixed start only, or start+end? How is its travel-in handled if back-to-back with another item?
- [ ] **OQ-8 — Delete semantics (1a).** "Remove from this Schedule" vs "reject the Option everywhere."
- [ ] **OQ-9 — Image source (3).** Google photo-reference-via-API vs Wikimedia-only vs both.

---

## Appendix

**Related documents:** [CONTEXT.md](../CONTEXT.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) ·
[ADRs 0001–0007](./adr/)

**Change Log**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-09 | zzzhushi | Initial draft from grilling session + ADRs 0001–0006 |
