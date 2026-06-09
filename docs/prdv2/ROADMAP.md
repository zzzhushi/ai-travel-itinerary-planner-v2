# Build Roadmap — AI Travel Itinerary Planner

**Status:** Planning complete; **no application code written yet.** This is the handoff for
the build. Last updated 2026-06-09.

---

## How to use this document

This is the entry point for an implementation session. Read in this order before coding:

1. [CONTEXT.md](../CONTEXT.md) — domain glossary (Trip, Category, Interest, Option, Rating,
   Chosen, Capacity, Schedule). Use these exact terms.
2. [docs/PRD.md](./PRD.md) — requirements: user stories + `FR-*`/`NFR-*` IDs + open questions.
3. [docs/ARCHITECTURE.md](./ARCHITECTURE.md) — package layout, interfaces, data model, schemas,
   data flow, config. **All file paths and interface names below come from here.**
4. [docs/adr/0001–0006](./adr/) — the decisions and *why*, so you don't relitigate them.

Then build phase by phase below. Each phase lists its goal, the files to create, the tasks,
the tests to write first (TDD), which requirements it satisfies, and its exit criteria.

---

## Working agreements (carry through every phase)

- **TDD.** Write the failing test first, then the code. Domain logic (validator, capacity,
  dedupe, rating) is deterministic — unit-test it directly. (Author reference: Matt Pocock TDD
  skill, noted in `raw_notes.md`.)
- **Core stays pure.** Nothing in `planner/` imports from `planner_cli/`. Effects go behind the
  `Protocol`s in ARCHITECTURE §5 ([ADR-0002](./adr/0002-ui-agnostic-core-cli-first.md)).
- **Default test run hits no network** — `FakeLLMProvider`/`FakeGeoProvider` + `:memory:` SQLite
  (NFR-003). Live tests are gated behind an env flag.
- **Every command opens an OTel span; `trace_id` == request id.** Print the request id to the
  user and stamp it on all logs ([ADR-0003](./adr/0003-otel-with-postgres-exporter.md)). This was
  an explicit author requirement.
- **Minimise LLM calls/tokens** (NFR-002): cache `(city, interest)`, batch gather per Category,
  only **Chosen** Options reach geocoding/scheduling.

---

## Resolved defaults — ⚠️ PROPOSED, confirm at start of Phase 0

These answer the PRD's Open Questions. They were *recommended* but **not yet confirmed by the
author** — confirm (or adjust) before relying on them; put them in `config.py` defaults.

| OQ | Setting | Proposed default |
|----|---------|------------------|
| OQ-2 | `GATHER_OPTIONS_N` (Options per Interest) | **5** |
| OQ-3 | `SLOTS_PER_PACE` | relaxed **3**, balanced **4**, packed **6**; meals are separate slots for Food |
| OQ-4 | `SCHEDULER_MAX_REPROMPTS` | **2** (≤3 attempts, then best-effort + `ValidationReport` warning) |
| OQ-5 | Force-include semantics | **Rating 5 = must-do** (force-included even at travel cost); 3–4 = candidate; no separate flag |
| OQ-1 | Zig-zag definition | quality metric: per-day travel **> 1.4× nearest-neighbour optimal**; hard cap by pace ≈ **90/120/150** min/day |

OQ-1 is the most consequential — it defines both the validator's hard check (Phase 5) and the
North Star metric. Settle it no later than Phase 4.

---

## Phase dependency graph

```
P0 scaffold ─┬─▶ P1 setup ─▶ P2 gather ─▶ P3 geo ─▶ P4 rate+gate ─▶ P5 schedule+validate ─▶ P6 render/diagnostics
             └─ (telemetry, config, repo iface, fakes used by all later phases)
                                                                                   later ─▶ P7 FastAPI+React
```

---

## Phase 0 — Scaffold & cross-cutting foundations

**Goal:** an installable package, config, persistence skeleton, telemetry, and fakes — so every
later phase has rails. No feature logic yet.

**Build:**
- `pyproject.toml` — deps (pydantic, pydantic-settings, typer, httpx, the chosen LLM/geo SDKs,
  opentelemetry-sdk + psycopg, pytest, hypothesis, ruff, mypy). Configure ruff/pytest/mypy.
- `.env.example` — keys + `LLM_CHAIN`, `POSTGRES_DSN`, `OLLAMA_*`, the OQ settings (ARCHITECTURE §8).
- `planner/config.py` — pydantic-settings loader; redaction of secret fields.
- `planner/domain/{models.py,enums.py,errors.py}` — the entities/enums/exceptions in ARCHITECTURE §4.
- `planner/repository/{interface.py,sqlite_repo.py,schema.sql}` — `Repository` Protocol + SQLite
  impl (file or `:memory:`); domain DDL ([ADR-0004](./adr/0004-sqlite-state-postgres-logs.md)).
- `planner/telemetry/{otel.py,pg_exporter.py}` — tracer/span helpers (trace_id = request id) +
  custom Postgres exporter writing `log_event`/`llm_call`; **console exporter fallback when
  `POSTGRES_DSN` absent** so the CLI runs without Postgres.
- `tests/fakes/` — `FakeLLMProvider`, `FakeGeoProvider`, in-memory repo fixtures.

**Tests first:** repository round-trip (save/load a Trip) on `:memory:`; config loads + redacts.

**Satisfies:** E1 (persistence substrate), E2 (telemetry substrate), NFR-001/003/006.

**Exit criteria:** `pytest` green with the repo + config tests; `planner --help` runs; a no-op
command emits a trace whose id is printed; everything installs from a clean venv.

---

## Phase 1 — Trip setup (Epic A)

**Goal:** create, persist, and resume a Trip with Categories + Interests.

**Build:** `planner/services/trip_setup.py`; default Categories in `domain/enums.py`;
`planner_cli/main.py` command `trip new` (prompt for city, `arrival_at`, `num_days`, pace,
daily window, transport mode, **Home Base lodging**; offer default Categories; add Interests).
Geocode the Home Base via the tier ladder (reuse Phase 3's geocoder, or stub until then).

**Tests first:** Day-1 slot reduction from a late `arrival_at`; empty Category allowed but flagged;
Trip reloads by id with full tree intact; **Home Base persists and geocodes**.

**Satisfies:** FR-001, FR-002, **FR-019**; Stories A1, A2, **A3**; E1; [ADR-0007](./adr/0007-anchors-and-anchor-aware-scheduling.md).

**Exit criteria:** `planner trip new` returns a `trip_id`; re-loading it yields the same tree;
tests green.

---

## Phase 2 — Option gathering (Epic B1) · first LLM contact

**Goal:** propose concrete Options per Interest via the `LLMProvider`, grounded + structured,
batched per Category, cached, de-duplicated.

**Build:**
- `planner/providers/llm/` — `interface.py` (`LLMProvider`), `chain.py` (`LLMChain` fallback on
  quota/rate-limit), and concrete providers per `LLM_CHAIN` (start with one real + the fake).
- `planner/providers/cache.py` — `(city, interest)` gather cache.
- `planner/services/gathering.py` — per-Category batched prompt, grounded gather, defensive JSON
  parse + one repair retry, dedupe by place/coords, persist Options + log `llm_call` tokens.
- CLI `gather TRIP` (gather portion).

**Tests first (with fakes):** cached `(city, interest)` ⇒ no new provider call (assert call count);
dedupe collapses near-identical Options; malformed JSON triggers repair then skip+log; chain falls
to next provider on a simulated quota error. Add one **cassette** test for real payload shape.

**Satisfies:** FR-003/004/005/006, FR-018, E3; Stories B1, E3;
[ADR-0006](./adr/0006-llm-provider-abstraction-fallback-chain.md). Honour NFR-002.

**Gotcha to remember:** grounding + strict response-schema may not compose in a single call —
request JSON in-prompt and parse defensively; **verify against current provider docs** (PRD risk).

**Exit criteria:** gather fills Options for a fake Trip deterministically under fakes; re-run makes
zero new calls; tokens recorded; tests green.

---

## Phase 3 — Geo resolution (Epic B2)

**Goal:** give each Option a verified location and build the travel matrix.

**Build:** `planner/providers/geo/` — `GeoProvider`/`TravelProvider` Protocols + `tiered.py`
(geocode Google→OSM→LLM-estimate, setting `geo_source`; travel Google DistanceMatrix→OSRM→
haversine) + geocode cache. `planner/services/geocoding.py` ties Options → coords → matrix for the
**Chosen** set per `transport_mode`. Wire into CLI `gather` (geo portion).

**Tests first (fakes):** tier fallthrough sets the right `geo_source`; matrix built only for Chosen
and for the Trip's mode; geocode cache prevents repeat lookups.

**Satisfies:** FR-007, FR-008; Story B2; [ADR-0001](./adr/0001-tiered-geo-sourcing.md).

**Gotcha:** respect Nominatim usage policy (rate/etiquette) — cache + throttle the OSM tier.

**Exit criteria:** every Option has coords + provenance; a travel matrix exists for Chosen; tests green.

---

## Phase 4 — Rating & Capacity gate (Epic C)

**Goal:** capture Ratings, derive the Chosen set, and give the advisory enough/too-many verdict.

**Build:** `planner/services/rating.py` (apply 1–5 Rating; Chosen = ≥3; unrated = excluded) and
`planner/services/capacity.py` (Capacity = days × slots-per-day by pace − Day-1 reduction;
over/undersupply messaging). CLI `rate TRIP` and `capacity TRIP`.

**Tests first:** Chosen boundary at 3; unrated excluded; Capacity math incl. partial Day-1;
oversupply reports trim count; undersupply suggests gathering; gate never blocks.

**Satisfies:** FR-009, FR-010; Stories C1, C2. **Confirm OQ-1, OQ-3, OQ-5 here at the latest.**

**Exit criteria:** ratings persist; `capacity` prints a correct verdict; tests green.

---

## Phase 5 — Scheduling & validation (Epic D1, D2) · the hard part

**Goal:** generate a travel-aware Schedule via the LLM and enforce quality deterministically.

**Build:**
- `planner/scheduling/prompt.py` — serialise Chosen + travel matrix + constraints/preferences
  (hard constraints AND soft weights `w_travel/w_rank/w_balance/w_pace`) into the schedule prompt.
  Include **Home Base** (day start/end) and any **Pinned Commitments** as fixed anchors, and bias
  toward **anchor-aware clustering** (nearby Options in slots adjacent to anchors) — ADR-0007.
- `planner/scheduling/validator.py` — `ScheduleValidator.check()` → `ValidationReport`
  (opening-hours violations, daily-window overflow, meal-slot misfit, per-day travel/zig-zag via
  OQ-1, **days start/end at Home Base**, **pins at exact time + unmoved on regen**, score).
- `planner/services/scheduling.py` — call `LLMProvider.schedule()`, validate, re-prompt up to
  `SCHEDULER_MAX_REPROMPTS`, else return best-effort flagged with the report; persist
  `schedule`/`schedule_item` incl. `travel_minutes_from_prev`; surface `InfeasibleConstraint`.
- CLI `schedule TRIP`.

**Tests first:** **property-based (Hypothesis)** — over random Options/constraints, emitted
Schedules never violate hours or the daily window (NFR-004); meal Options land in meal windows;
Day-1 starts at `arrival_at`; infeasible Must-do raises `InfeasibleConstraint` (not silent drop);
re-prompt cap respected.

**Satisfies:** FR-011/012/013/014/015, **FR-019/020**; Stories D1, D2;
[ADR-0005](./adr/0005-deterministic-travel-aware-scheduler.md), [ADR-0007](./adr/0007-anchors-and-anchor-aware-scheduling.md).

**Exit criteria:** with a fake LLM returning a known-bad then good Schedule, the service re-prompts
and emits a validated Schedule; property tests green.

---

## Phase 6 — Output & diagnostics polish (Epic D3, E2)

**Goal:** render the Schedule for humans and make runs fully diagnosable.

**Build:** CLI `show TRIP` (per-day render with times + travel between Options); optional one-call
LLM prose day summary. Confirm telemetry: each command's `trace_id` printed; logs + tokens queryable
in Postgres by `trace_id`/`trip_id`; verify the documented query works.

**Tests first:** renderer formats a known Schedule deterministically; a run produces correlated
`log_event`/`llm_call` rows (against a test Postgres or the exporter's seam).

**Satisfies:** FR-016, FR-017; Stories D3, E2.

**Exit criteria:** a full `trip new → gather → rate → schedule → show` walkthrough works end-to-end
on fakes; a real request id can be traced to its log rows.

---

## Phase 7 — FastAPI + React (later; PRD Phase 2)

Out of scope for the first build. When reached: a FastAPI app over the same `services/*`,
returning `trace_id` as `X-Request-ID`; a React frontend for ranking + Schedule/map visualisation;
optionally the `SearchProvider` so non-grounding models still get real places. The core must not
change shape to support this (that's the point of ADR-0002).

---

## Future requirements (post-MVP, triaged 2026-06-09)

Full catalogue + verdicts in [PRD.md → Future Requirements & Triage](./PRD.md#future-requirements--triage);
where each plugs into the code in [ARCHITECTURE.md §12](./ARCHITECTURE.md#12-future-seams-planned-not-built--see-prd-future-requirements--triage).
Seams are in place so these aren't rewrites:

- **Next (post-MVP):** Pinned Commitments add-UX (wedding/locked tickets) — ADR-0007 seam already
  in the scheduler; user-added Options; per-Option duration override; buffer; `trip list`.
- **P2 (with web UI):** images, map view, delete/edit schedule items.
- **Deferred (note the seam):** flights+transfers, multi-city (`Trip` → `CityStay`), and the
  **non-technical-user** experience (init wizard, default Ollama, optional JSON repo, packaged
  app, per-OS docs — documented as a goal, not yet built).
- **New open questions:** OQ-6 buffer model, OQ-7 pin time semantics, OQ-8 delete semantics,
  OQ-9 image source (in PRD).

---

## Definition of done — CLI MVP (Phases 0–6)

- A traveller can `trip new → gather → rate → capacity → schedule → show` for a real city.
- Schedules respect hours/meal/window/Day-1 and minimise travel (validator passes; OQ-1 honoured).
- Re-runs reuse caches; planning survives one provider's free-tier exhaustion via the chain.
- Default `pytest` runs offline and green, including Hypothesis property tests on the validator.
- Any run is traceable from its printed request id to Postgres logs with token counts.

## First action for the next session

1. Confirm/adjust the **PROPOSED defaults** table above (esp. OQ-1).
2. Start **Phase 0**: `pyproject.toml`, `config.py`, `domain/`, `repository/` (+ `:memory:`),
   `telemetry/` (with console-exporter fallback), and `tests/fakes/`.
3. Write the first failing test (repository round-trip) before its implementation.
