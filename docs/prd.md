# PRD — AI Travel Itinerary Planner

Date: 2026-06-09
Status: Draft v1 (post-interview)
Owner: zzzhushi

---

## 1. Problem & Goal

A traveller landing in a new city for a few days struggles to turn their interests
into a **realistic day-by-day plan that doesn't waste time criss-crossing the city**.
Manual planning means juggling opening hours, travel time, meals, fixed commitments
(flights, tickets, events), and personal taste — all at once.

**Goal:** a locally-run tool that takes a city, dates, anchors (hotel/flights/tickets),
preferences, and interests, suggests *real* places, lets the user rank them, and builds
a geographically-sane, time-feasible, day-by-day itinerary the user can refine.

### Success definition (v1)
- The engine **never violates** its hard correctness invariants (§13).
- A user can go from an empty `trip.yaml` to a usable multi-day itinerary in one run.
- Quality is judged by the **user** (human-in-the-loop), who refines via levers, locks,
  and feedback until satisfied. No automated quality scoring in v1.

---

## 2. Users & Scope

**Primary persona:** an independent traveller / small party planning their own trip,
comfortable editing a config file or using a simple local UI. Not a travel agency, not
a multi-tenant SaaS.

**In scope (v1):**
- Single **city** per trip.
- Single **party** (one shared set of preferences — no multi-person preference reconciliation).
- Trip length **1–14 days**.
- Planning and **linking out** to places.

**Out of scope (v1):** see §17.

---

## 3. Core Concepts (the two ideas everything hangs on)

### 3.1 Anchors — one primitive for every fixed point
Hotels, flights, trains, weddings, pre-bought tickets, and manual buffers (e.g. customs)
are all the **same primitive**:

```
Anchor = { kind, location?, start?, end?/duration, day?, movable }
```

- **Fixed anchors** — immovable in time *and* day. Flight arrival/departure, ticketed
  event (Disneyland 5h), wedding, manual buffer. The scheduler treats these as **walls**
  and builds around them; it never negotiates them.
- **Soft anchor** — the hotel. Recurs daily as each day's **start and end point**, anchors
  geographic clustering, but has no fixed activity time.
- **User locks** — when the user likes a place/day during refinement, the lock makes it a
  **temporary fixed anchor** for the next solve. Same machinery, no new code.

Day-1 / last-day asymmetry falls out for free: a 6pm flight arrival is a fixed anchor that
makes everything before `arrival + customs_buffer + airport→hotel travel` unschedulable.
Departure day mirrors it (hard stop at `flight − checkin_lead − hotel→airport travel`).

### 3.2 The LLM ↔ Scheduler contract — "words → numbers once; optimize numbers every time"
The **LLM does only fuzzy work** (suggest, rank, theme, interpret free-text feedback).
The **scheduler is deterministic** and does all the hard work (geocode, travel time,
cluster, schedule, validate, explain). They meet at a strict structured contract:

```
place   = { id, name, coords, category, interest_score, duration_min,
            hours, tod_affinity, price_level, must_see, locked, source, confidence }
anchors = [ Anchor, ... ]
prefs   = { w_interest, w_travel, w_pace, pace, walk_threshold_min,
            mode, meal_slots, day_window, budget }
travel  = matrix(places)   # real ORS, or haversine fallback
```

By the time the scheduler runs, **every preference is already a number or a constraint**.
This is why the scheduler needs no LLM to honor preferences (see §8).

---

## 4. End-to-End Flow

1. **Input** — user fills `trip.yaml` (§12) or runs an interactive wizard that emits it.
2. **Curate** — one **batched** LLM call returns candidate places per interest category,
   each with a proposed `duration_min`, a `why` note, and a preliminary rank.
3. **Resolve** — deterministic: geocode each place (Nominatim), enrich opening hours and
   duration via the resolver chain (§9), drop-and-backfill hallucinations.
4. **Rank** — user reviews candidates (colored by category), inspects details, sets their
   own ratings, and flags **must-sees**. `interest_score = blend(user_rating, llm_rank) ×
   category_weight`, user rating dominant. (Auto-rank is the default/non-interactive path
   used by tests.)
5. **Schedule** — deterministic: anchor-aware clustering → day assignment → per-day route
   ordering → constraint validation → explanation (§8).
6. **Review & refine** — user reads the itinerary + the map + the explanations, then:
   - tweaks **geometry levers** (free, instant re-solve), or
   - **locks** good parts and **regenerates** a day/slot with structured + free-text feedback
     (metered LLM call), or
   - reverts to a previous **version**.
7. **Finalize** — optional "Generate real routes" button fetches street polylines + exact
   segment times for the chosen legs and re-validates timing (§7).

---

## 5. Architecture

**Layered, interface-independent. The value and the tests live in a pure-Python engine.**

```
┌─────────────────────────────────────────────────────────┐
│  Clients                                                 │
│   • CLI (v1)            • NiceGUI drag + map UI (v2)      │
└───────────────┬─────────────────────────┬───────────────┘
                │  (both are API clients)  │
┌───────────────▼─────────────────────────▼───────────────┐
│  FastAPI service layer  (localhost, uvicorn — no deploy) │
└───────────────────────────┬─────────────────────────────┘
┌───────────────────────────▼─────────────────────────────┐
│  Engine (pure Python package, fully unit-tested)         │
│   curator(LLM) • resolver • clusterer • scheduler        │
│   • explainer • feedback/levers • versioning             │
└───────────────────────────┬─────────────────────────────┘
┌───────────────────────────▼─────────────────────────────┐
│  Adapters (swappable, cached): Gemini • Nominatim •      │
│   Overpass • ORS • Open-Meteo • Foursquare(opt)          │
└─────────────────────────────────────────────────────────┘
```

- **"Local" = no hosted backend of ours.** External APIs are allowed if **free-tier with
  usable limits**. The only required secret is the **Gemini key**.
- **The engine is the core library; clients are thin.** The CLI calls the engine
  **directly** (no HTTP needed); the FastAPI layer wraps the *same* engine for the v2
  NiceGUI UI and for the OTel/request-id boundary. The diagram shows logical layering, not a
  mandatory HTTP hop for the CLI.
- **Adapters are cached and swappable** — enables deterministic tests, offline fallback,
  and clean upgrades (e.g. Nominatim → Google Places later).

**Tech:** Python 3.11+, FastAPI + uvicorn, Pydantic v2 (schemas/validation), `pytest`,
`gemini-2.0-flash-lite` default model, OpenTelemetry SDK + FastAPI instrumentation
(diagnostics, §13.2), NiceGUI + Leaflet (v2 UI).

### 5.1 Persistence & State

Decided at strategy level here (it shapes V1); exact schemas/eviction/rotation defer to the
milestone task-breakdown. **No server database** — that would reintroduce the hosted
dependency we ruled out.

| What | Store | Why |
|---|---|---|
| App state — `trip.yaml`, rankings, locks, **itinerary versions** | **Files** in a per-trip directory (`trip.yaml` + numbered JSON version snapshots) | Human-readable, git-diffable, trivially testable, matches "runs locally"; version history = revert by snapshot |
| Response cache — LLM / geocode / hours / routing | **SQLite** (stdlib, single file) | Keyed lookups + TTL + hit-rate queries; still local/no-server; powers deterministic tests + offline fallback |
| Diagnostics logs | **JSONL files** (§13.2) | Greppable, standard, simple; load into SQLite/DuckDB *ad hoc* for analysis — do **not** build a logging DB |

**Layout.** `trips/<trip_id>/` holds the spec + numbered version snapshots;
`runs/<trip_id>/<run_id>/` holds that run's `manifest.json` + `trace.jsonl`. Cache keys are
**per-adapter** — geocode by query, matrix by coord-set, Curator by `(city, interests,
prefs-hash)` — not one global key.

A DB for app state (or Postgres anywhere) earns its place only with cross-trip queries,
concurrency, or multi-user — all out of scope for v1.

### 5.2 API surface (contract sketch)

Contract designed now; **built at V6 (refinement loop), consumed by the UI at V7**. A local CLI can
call the engine as a library — HTTP becomes load-bearing for the v2 UI. Building the FastAPI
layer earlier is a deliberate choice justified by the OTel/observability learning goal and
the request-id debugging affordance below, not a hard requirement for the CLI.

The resource is a **trip** and its **itinerary versions**; endpoints are §4's flow exposed.
Synchronous (operations are seconds); streaming/async deferred.

| Method · Path | Intent | Internal calls | Returns |
|---|---|---|---|
| `POST /trips` | create from spec | validate → file store | `trip_id`, normalized spec |
| `GET /trips/{id}` | view trip + state | file store | trip + rankings + current version ref |
| `POST /trips/{id}/candidates` | suggest places to rank | Curator (Gemini, 1 batched) → geocode (Nominatim) → hours/duration resolvers → drop-&-backfill; Overpass on degrade | candidate pool/category w/ `source`+`confidence` |
| `PATCH /trips/{id}/rankings` | submit ratings | persist → recompute `interest_score` | updated rankings |
| `POST /trips/{id}/plan` | build itinerary | (cached or) ORS matrix ·1–2; Open-Meteo; deterministic scheduler | new version (JSON + Markdown) + explanations |
| `POST /trips/{id}/refine` | tweak / regenerate | geometry levers → deterministic re-solve (0 LLM); content → Editor (Gemini, 1); locks → temp anchors | new version |
| `GET /trips/{id}/versions` | history | file store | version list |
| `POST /trips/{id}/versions/{v}/restore` | revert | file store | restored version |
| `POST /trips/{id}/routes` | real street routes | ORS directions per leg → re-validate timing | itinerary w/ polylines + drift flags |
| `GET /healthz` | liveness | — | ok |

**Response envelope.** One identifier, three names: the API `request_id`, the engine
`run_id`, and the OpenTelemetry `trace_id` are the **same value**. A returned id is the
handle to that request's full span tree (`runs/<trip_id>/<run_id>/trace.jsonl`):

```
success → { request_id, trace_id, trip_id, version,
            data: {...},
            diagnostics: { llm_calls, cache_hits, warnings: [...] } }
error   → { request_id, trace_id,
            error: { code, message, stage, detail } }
```

---

## 6. External Data Sources

| Concern | Primary (free) | Fallback | Notes |
|---|---|---|---|
| LLM | Gemini `flash-lite` (free tier) | cache → deterministic mode | only required key |
| Geocoding | Nominatim (OSM, no key) | cached results | ≤1 req/s, requires User-Agent |
| Places by category | Overpass (OSM, no key) | — | powers deterministic fallback |
| Travel-time matrix | OpenRouteService matrix (free key) | haversine × mode speed | ~1–2 calls/city; verify quota |
| Route polylines (display) | ORS / OSRM directions | none (omit lines) | on-demand only, ~15–20 segments/trip |
| Opening hours | OSM `opening_hours` | Wikidata → Foursquare(opt) → LLM → category default → assume-open+flag | day-of-week aware |
| Weather | Open-Meteo (no key) | skip | drives indoor/outdoor demotion |

> Free-tier ceilings drift — the implementation must **verify current quotas** and degrade
> gracefully (§11), never hard-fail on quota.

---

## 7. Travel-Time Model (two tiers)

Routing is **two separate problems** with different costs:

1. **Matrix (for planning).** ORS matrix endpoint returns travel times among the whole
   candidate set (~30–40 places) in **~1–2 calls** — cheap and accurate, including cities
   where straight-line lies (rivers, bays, hills). Haversine × mode-speed is the **fallback**.
2. **Polyline (for display only).** Real street paths are needed only for the *finalized,
   consecutive* legs (~15–20 per trip). Fetched **on demand** via a "Generate real routes"
   button; also re-validates each day against exact segment times and flags drift.

**Two-tier optimization within the matrix:**
- **Short hops (≤ `walk_threshold_min`)** → flat walk estimate, **no routing call** (nobody
  taxis 150m). The geographic clusters used for day-assignment double as the tier boundary:
  *within* a cluster you mostly walk.
- **Long hops (between clusters, hotel↔cluster)** → real ORS routing, mode-aware.

`walk_threshold_min` is the same lever as the user's travel-mode preference ("I'll walk up
to N minutes").

---

## 8. The Scheduler (deterministic)

### 8.1 Pipeline
1. **Assign fixed anchors to their days first** (they are walls).
2. **Anchor-aware geographic clustering** of flexible places into N day-clusters
   (e.g. k-means on coords), seeding clusters near each day's anchors and the hotel.
   A day may hold **multiple clusters** when one neighborhood is thin; inter-cluster travel
   becomes a **penalty term**, not a hard block — the optimizer only splits a day when the
   place-quality gain outweighs the travel cost.
3. **Per-day selection + ordering** via greedy nearest-neighbor + local search (small TSP
   heuristic) from the hotel anchor, inserting travel time between consecutive stops.
4. **Validate** against hard constraints; **move-then-drop** any place that can't fit.
5. **Explain** every non-trivial decision (§8.4).

### 8.2 Objective function (soft)
```
score =  w_interest · Σ(interest_score)
       − w_travel   · (total_travel_time + inter_cluster_penalty)
       − w_pace     · (overpacking_penalty)
```
Defaults encode the user's ranking: **interest > travel > pace**
(e.g. `w_interest 0.5 / w_travel 0.3 / w_pace 0.2`).

> **Three distinct "weights" — don't conflate:** (1) per-category `weight` in `trip.yaml`
> scales how much a category contributes to a place's `interest_score`; (2) `interest_score`
> (0–1) per place = `blend(user_rating, llm_rank) × category_weight`; (3) the global
> coefficients `w_interest / w_travel / w_pace` (the tunable levers) trade the three soft
> terms against each other. Only (3) are the "levers."

> **Design tension recorded:** the stated core pain was "criss-crossing," but the user
> ranked *interest match above travel tightness*. Accepted consequence: the tool will
> sometimes spread a day out to reach a strongly-matching place. Tunable via levers below.

### 8.3 Constraints
**Hard (never violated):**
- Each day starts and ends at the hotel anchor.
- Fixed anchors appear at their exact time/day, unmoved.
- No two activities overlap; travel time inserted between consecutive stops.
- No activity scheduled outside its resolved opening hours (day-of-week aware).
- Each day fits its `day_window`.
- Stops/day never exceed the pace **hard ceiling** (relaxed/balanced/packed → max stops).
  Breathing room *within* that ceiling is the soft `overpacking_penalty` (§8.2), not a hard rule.

**Soft (optimized, configurable):**
- Meal slots (lunch/dinner; optionally coffee/dessert as a preference).
- Time-of-day affinity (viewpoints→sunset, markets→morning, nightlife→night).
- Fatigue pacing (don't stack heavy stops; gentle day-1 if late arrival).
- Weather (rain demotes outdoor, promotes indoor — Open-Meteo).

**Must-sees** are *near-hard*: try to **move** to a day that fits; if impossible, **drop**
and **surface the reason** to the user. Never silently swallowed.

> **Budget & accessibility** are *captured* in the spec (`price_level`, `budget_per_day`)
> but **enforcement is a fast-follow**, not wired into the v1 objective/constraints.

### 8.4 Explainability (a first-class feature, doubles as diagnostics)
The itinerary surfaces *why*, not just *what*. Every drop / move / unverified place carries
a human-readable reason the user can read, e.g.:
> *"Musée d'Orsay is only open Tue; Tue is full with your Disneyland anchor → couldn't fit."*

---

## 9. Place Data Resolution (resolver chains)

Each resolved value carries a **`source` + `confidence`**, logged to diagnostics. A user
override always wins on top.

- **Opening hours:** OSM `opening_hours` → Wikidata/Wikipedia → Foursquare (opt) → LLM
  estimate → category-default hours → **assume-open + flag**. Must answer "open at *this
  datetime*," handling Monday museum closures, weekend-only markets, service-hour gaps.
- **Visit duration:** user override → LLM per-place proposal (size/popularity-aware) →
  **category default** (sightseeing 2h, museum 2h, meal 1h, café 45m, park 1h, viewpoint
  30m) → fallback constant. Category defaults are **user-editable**.

**Hallucination handling:** any place that won't geocode is **dropped and backfilled**
(ask the Curator to top up, or pull from the over-fetched pool), with the drop logged so
hallucination rate is observable.

---

## 10. LLM Call Model (NOT agentic)

**No autonomous agents / tool-loops.** Those make call count unpredictable, are hard to
test, and would threaten the free tier. Instead: **discrete, single-shot, schema-constrained
calls at fixed pipeline stages.** Full prompts + output schemas live in `docs/prompts.md`.

**Roles (2 real + 1 cosmetic):**
- **Curator** — suggest candidate places per interest (+ duration, why, prelim rank). **1
  batched call** for the whole trip (never one-per-category).
- **Editor** — interpret free-text / content feedback → re-suggest or re-rank. On-demand.
- **Narrator** (optional) — friendly day summaries; mergeable or skippable.

**Call budget per trip:**
- Baseline plan: **1 call** (batched, over-fetched ~8/category).
- Each **content** regeneration: **1 call**.
- Each **geometry** lever change: **0 calls** (deterministic re-solve).
- Identical/cached trip: **0 calls**.
- Typical session (~5 refinements): **~6 calls** — <1% of Gemini's free daily tier.

**Minimization playbook:**
1. Batch across categories. 2. Over-fetch candidates. 3. Cache by `(city, interests,
prefs-hash)` (also powers tests + offline mode). 4. Split regen into free-geometry vs
metered-content loops. 5. Use `flash-lite` for structured work. 6. Bounded self-heal:
schema-validation failure re-prompts **at most once**, then degrades.

---

## 11. LLM/API Failure Handling

| Failure | Flow |
|---|---|
| Transient (timeout, 5xx) | retry with exponential backoff, capped (3) |
| Rate limit / quota (429) | back off → cache → degrade |
| Malformed output | enforce structured output (response schema), parse with Pydantic |
| Schema violation | self-heal: re-prompt once with the validation error, then degrade |
| Hallucinated place | drop-and-backfill, log drop rate |
| Refusal / empty | treat as schema failure → degrade |
| Slow / non-deterministic | cache by request hash; tests run against cache |

**Degradation floor (decided):** cache → **deterministic non-LLM mode**. When Gemini is
fully unavailable and uncached, query **Overpass** for top-tagged places per category and
let the deterministic scheduler build a plain (unranked-curation) itinerary. **The product
always produces something real**, because all load-bearing logic is deterministic. A local
Ollama LLM fallback is explicitly a future extension, not v1.

---

## 12. Trip Spec (`trip.yaml`) — the single reproducible input

```yaml
city: "Paris"
dates: { start: 2026-09-10, end: 2026-09-13 }
hotel: { name: "Hôtel X", address: "..." }        # soft anchor

anchors:                                            # fixed anchors
  - { kind: flight_arrival, datetime: 2026-09-10T18:00, airport: CDG,
      buffers: { egress_min: 45, to_hotel_min: 60 } }
  - { kind: ticket, name: "Disneyland", day: 2026-09-12, start: "10:00",
      duration_min: 300, location: "..." }
  - { kind: event, name: "Wedding", day: 2026-09-11, start: "16:00",
      duration_min: 240, location: "...", movable: false }
  - { kind: flight_departure, datetime: 2026-09-13T19:00, airport: CDG,
      buffers: { checkin_lead_min: 120, to_airport_min: 60 } }

preferences:
  pace: relaxed                 # relaxed | balanced | packed  → stops/day
  mode: walking                 # walking | transit | taxi
  walk_threshold_min: 20
  day_window: { start: "09:00", end: "19:00" }
  meal_slots: [lunch, dinner]   # + coffee/dessert optional
  budget_per_day: null
  weights: { interest: 0.5, travel: 0.3, pace: 0.2 }   # tunable levers
  content: { vibe: "more local, fewer tourist traps" }  # LLM lever (free-text)

interests:                       # fixed set + user-defined
  - { category: food, weight: 5 }
  - { category: culture, weight: 4 }
  - { category: sightseeing, weight: 3 }
  - { category: "specialty coffee", weight: 4 }   # custom

# Populated/updated by the run; persisted so a run is replayable:
rankings: {}                     # user ratings per place
locks: []                        # temporary anchors
```

Fixed interest categories: **food, culture, sightseeing, nature/outdoors, nightlife,
shopping, relaxation**, plus user-defined categories.

---

## 13. Non-Functional Requirements

### 13.1 Testing (hard requirement)
Split **correctness** (testable, gates CI) from **quality** (human-judged, not automated).

**Correctness — invariant/property tests** on synthetic fixtures with mocked geodata, no
network, deterministic. The engine must **never** violate:
- Every day starts and ends at the hotel anchor.
- No overlaps; travel time inserted; day fits `day_window`.
- Every fixed anchor at its exact time/day, unmoved.
- No activity outside resolved opening hours (day-of-week aware).
- Stops/day never exceed the pace hard ceiling.
- Every dropped place has a logged reason; every must-see is scheduled **or** surfaced as
  un-fittable with a reason.

**LLM-layer tests:** recorded/cached responses (VCR-style) so they're deterministic;
schema-validation tests; a hallucination test (feed a non-geocoding place → assert
drop-and-backfill).

**Quality:** judged by the user via the refine loop. **LLM-as-judge eval is out of scope.**
Golden-output tests only for pure-deterministic transforms (clustering, route ordering).

### 13.2 Diagnostics — agent-debuggable logging (hard requirement)

**Design target:** from a **run directory alone** (no re-run, no original session), a coding
agent must be able to (1) **localize** a failure to a pipeline stage, (2) **explain** any
decision from the data behind it, and (3) **deterministically replay** the run. Ordinary
"human-skimmable" logging is not sufficient.

Built on **OpenTelemetry** (traces as the primary signal; FastAPI auto-instrumented). Stages
→ spans, decisions → span events, provenance → span attributes. A **custom JSONL exporter**
maps spans to the agent-debuggable schema below (see `docs/logging.md`); an optional OTLP
exporter can push to a local Jaeger/Tempo container. Replay (capability #4) stays independent
of telemetry — its source is the manifest + cache.

Structured **JSONL**, one event per line, stable schema. Required capabilities:

1. **Localize** — every line carries `run_id` / `trip_id` / `version` + `stage` + `component`
   + a stable `event` code. Each pipeline boundary (curate → resolve → cluster → schedule)
   logs its **input and output** (value or hash) so a bug bisects to the stage that caused it.
2. **Explain with provenance** — decision events carry the *data behind the verdict*, e.g.
   `dropped X: must_see, open Tue only, Tue saturated by anchor 'Disneyland', Δobjective −0.4`
   — the machine twin of the human explanation (§8.4). Also: resolver decisions (`source` +
   `confidence`), scheduler moves/drops/penalties, hallucination drop rate, per-run LLM count.
3. **Trace external calls** — service, endpoint, params (or hash), latency, status, **cache
   hit/miss**, retry count, quota state, and **fallback taken** (`Gemini 429 → cache`,
   `→ Overpass degrade`).
4. **Replay** — a **run manifest** (config snapshot, model id, **prompt version/hash**, RNG
   seeds) + the SQLite response cache lets the engine re-run the trip **offline** and
   reproduce the same itinerary and decision trace. This reuses the existing cache + the
   deterministic engine — replay and test-determinism are the *same* mechanism.
5. **Diff** — manifest model/prompt/config/code versions reveal *what changed* when output
   changes.

**Meta:** a documented **event catalog** (`docs/logging.md`) lists every `event` code + its
fields; standard levels (DEBUG/INFO/WARN/ERROR) and filtering by `run_id`/`stage`; errors
always carry the failing input + full context.

**Acceptance bar (testable):** *given only a run directory (manifest + JSONL trace + cache),
`replay` reproduces the identical itinerary and decision log offline.* This single test both
proves the logs are debug-complete and serves as the engine-determinism guarantee.

Human-readable reasons are surfaced in the itinerary (§8.4); full machine detail goes to the log.

### 13.3 Performance
- Geometry re-solve (lever change): **sub-second**, no network.
- Baseline plan: bounded by 1 LLM call + 1–2 matrix calls + cached geocoding.

### 13.4 Documentation (hard requirement)
- **README** — setup, obtaining a Gemini key, running the CLI, configuring `trip.yaml`.
- **`trip.yaml` reference + worked example** (§12 is the seed).
- **API docs** — FastAPI's auto-generated OpenAPI/Swagger, kept accurate via Pydantic schemas.
- **Code docstrings** on engine modules; the **LLM↔scheduler contract** (§3.2) and the
  **anchor model** (§3.1) documented as the load-bearing concepts.
- **Architecture overview** — this PRD plus a short top-level diagram in the README.

---

## 14. UI

### CLI (v1)
`plan trip.yaml` → Markdown itinerary (with explanations) + JSON sidecar (test target).
Interactive ranking available; auto-rank is the default and the test path.

### NiceGUI drag + map UI (v2)
Pure Python (no React/JS), built on FastAPI — same stack. Earns its existence by doing what
the CLI can't:
- **Read-only Leaflet map**, pins **colored + numbered by day**, showing each day's visual
  flow. No connecting lines in v1 (distance is readable from the map); real polylines only
  via the on-demand button.
- **Drag-to-reorder** places between/within days (in the list; map mirrors live).
- **Rating pane**, places colored by category, the rated place **highlighted on the map**.
- **Lock** controls (→ temporary anchors), **lever sliders** (free re-solve), **feedback
  box** (metered), **version history** to revert.

Reflex is the fallback if NiceGUI proves limiting. Streamlit rejected (weak drag; would
just mirror the CLI).

---

## 15. Output Format

- **Markdown** itinerary: per-day schedule with times, durations, travel legs, and the
  human-readable explanations.
- **JSON sidecar**: machine-readable, the assertion target for tests.
- Optional later: exported map / shareable file.

---

## 16. Milestones (vertical slices)

Each milestone is an **end-to-end, runnable increment**, not a layer. Build the thin path
first, then deepen. **OpenTelemetry span instrumentation, invariant tests, and JSONL logging
are a standing definition-of-done on every milestone**, not a one-time task.

**MVP cut line:** **V1–V3** is already a genuinely useful planner (realistic, anchored,
non-criss-crossing trips from the CLI). V4–V6 deepen quality/resilience/refinement; **V7 (UI)
is optional/last**; V8 ships it.

- **V1 — Walking skeleton: plan a trivial trip end-to-end.**
  - *Exit:* From a minimal `trip.yaml` (city, dates, interests; no anchors), `plan trip.yaml`
    emits a real, geocoded, day-by-day Markdown+JSON itinerary; the run writes a JSONL trace +
    manifest; one invariant test passes in CI.
  - *Tasks:* Package layout + CLI entry; Pydantic schemas + `trip.yaml` loader; Gemini
    key/config; SQLite cache; OTel→JSONL logger; one Curator call; Nominatim geocode; naive
    day-fill scheduler (no travel/anchors); Markdown+JSON output; invariant-test harness in CI.

- **V2 — Geographically-sane days (kills criss-crossing).**
  - *Exit:* Multi-day itineraries cluster by neighborhood; each day starts/ends at the hotel;
    order minimizes travel (haversine two-tier); opening-hours, day-window and no-overlap
    enforced; un-fittable places dropped with a readable reason. Invariant tests cover all hard
    constraints.
  - *Tasks:* Anchor-aware geo clustering; nearest-neighbor ordering from hotel; two-tier travel
    (haversine + walk threshold); hours/duration resolver chains (source+confidence);
    hard-constraint validation; move-then-drop; explainability layer; expand invariant tests.

- **V3 — Anchors & realistic pacing.**
  - *Exit:* A trip with a 6pm flight arrival (+buffers), a ticketed multi-hour activity, and a
    fixed event schedules correctly around them; departure day truncates; meal slots,
    time-of-day affinity and fatigue pacing apply. Tests cover anchor immovability and
    day-1/last-day truncation.
  - *Tasks:* Fixed/soft anchors + buffers; arrival/departure-day truncation; soft constraints
    (meals, tod affinity, fatigue); objective function + default weights; multi-cluster day with
    inter-cluster penalty; anchor invariant tests.

- **V4 — Curation quality & resilience.**
  - *Exit:* User can inspect/rate candidates and flag must-sees, and ratings change the plan;
    over-fetch + drop-and-backfill keep categories full; with Gemini disabled the tool still
    produces a real (Overpass) itinerary; cached LLM responses make tests deterministic;
    `replay` reproduces a run from its run-dir.
  - *Tasks:* Interactive + auto ranking; `interest_score` blend; must-see flag; over-fetch +
    drop-and-backfill; full resolver fallbacks (Wikidata/Foursquare/LLM); LLM failure handling +
    Overpass degrade; response cache/VCR tests; `replay` command + acceptance test.

- **V5 — Travel-time accuracy & weather.**
  - *Exit:* Scheduler uses the real ORS matrix when available (haversine fallback); rainy days
    demote outdoor / promote indoor (Open-Meteo); an on-demand "real routes" action returns
    street polylines and re-validates day timing, flagging drift. Existing tests stay green.
  - *Tasks:* ORS matrix + haversine fallback; mode-aware long-hop routing; Open-Meteo weather
    demotion; on-demand polyline endpoint + timing re-validation/drift flags; quota handling +
    caching.

- **V6 — Refinement loop & API.**
  - *Exit:* Via FastAPI, the user can adjust geometry levers (instant, no LLM), regenerate a
    day/slot with free-text + structured feedback (Editor), lock places (→ temp anchors), and
    revert to a prior version; every response returns a `request_id` that resolves to its trace.
  - *Tasks:* FastAPI + response envelope (`request_id`=`trace_id`); geometry-lever deterministic
    re-solve; Editor content regeneration; locks as temp anchors; version snapshots + restore;
    per-trip file-store versioning.

- **V7 — Map UI (NiceGUI).**
  - *Exit:* A local NiceGUI app shows the itinerary on a read-only Leaflet map (pins colored +
    numbered by day), a category-colored rating pane that highlights the selected place on the
    map, drag-to-reorder, lever sliders, a feedback box, and version history — all over the V6
    API.
  - *Tasks:* NiceGUI app on FastAPI; Leaflet map (colored/numbered by day); rating pane with map
    highlight; drag-reorder list; lever sliders (free re-solve); feedback box (metered);
    version-history UI; "generate real routes" button.

- **V8 — Productionize & release.**
  - *Exit:* A fresh clone goes install → configured key → first itinerary using only the README;
    OpenAPI docs published; engine modules have docstrings; end-to-end smoke test green;
    error/UX messages clear; logging event-catalog matches emitted spans.
  - *Tasks:* Packaging/install (pyproject, entry point); `.env`/secrets handling; README +
    `trip.yaml` reference; OpenAPI/docstrings (§13.4); end-to-end smoke test; error-message UX
    pass; verify event-catalog vs emitted spans.

**v1 product = V1–V6** (CLI + API + refinement, fully tested). **v2 = V7** (UI). **V8** is the
release pass and can run partly in parallel.

---

## 17. Out of Scope (v1)

- Multi-city / multi-leg trips.
- Multi-person preference reconciliation (parties that disagree).
- Booking, ticket purchase, or live-availability checks (plan + link out only).
- LLM-as-judge / automated quality scoring.
- Local Ollama LLM fallback.
- React front-end; full map-manipulation (drag pins on the map).
- Paid APIs (Google Places/Directions) — clean upgrade path only.

---

## 18. Assumptions & Risks

- **A:** Gemini free tier sustains a single user's planning volume. *Risk: low* (typical
  session ~6 calls vs thousands/day).
- **A:** OSM/Nominatim/Overpass coverage is adequate for target cities. *Risk: medium* —
  thin coverage degrades suggestions; mitigated by LLM curation + hours resolver + Foursquare
  option. Flag low-confidence data in diagnostics.
- **A:** ORS free-tier matrix/directions quotas suffice at ~1–2 matrix calls/city + on-demand
  polylines. *Risk: low–medium* — verify current quotas; haversine fallback covers outages.
- **R:** Haversine underestimates in barrier cities (rivers/bays/hills) → optimistic
  schedules. *Mitigation:* prefer ORS matrix; on-demand real-route re-validation flags drift.
- **R:** Opening-hours data is patchy → "assume-open" mistakes. *Mitigation:* confidence
  flags surfaced to the user; resolver chain.

---

## 19. Open Questions

- Exact ORS free-tier matrix/directions limits at build time (verify, set per-day call caps).
- Concrete pace → stops/day mapping (e.g. relaxed 3–4, balanced 5, packed 6–7) — tune in V2.
- Whether per-slot regeneration is needed in v1 or per-day suffices (start per-day).
- Default candidate over-fetch count per category (start ~8).
- Version-history retention/pruning policy and its owner (keep-all in v1, or cap at N?).
- How the user flags must-sees (a `rankings` field vs a per-interest list in the spec).
