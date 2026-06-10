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
- The engine **never violates** its hard correctness invariants (Section 13).
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

**Out of scope (v1):** see Section 17.

---

## 3. Core Concepts (the two ideas everything hangs on)

### 3.1 Anchors — one primitive for every fixed point
Hotels, flights, trains, weddings, pre-bought tickets, and manual buffers (e.g. customs)
are all the **same primitive**:

```
Anchor = { kind, location?, start?, end?/duration, day?, movability }
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
This is why the scheduler needs no LLM to honor preferences (see Section 8).

---

## 4. End-to-End Flow

1. **Input** — user fills `trip.yaml` (Section 12) or runs an interactive wizard that emits it.
2. **Curate** — one **batched** LLM call returns candidate places per interest category,
   each with a proposed `duration_min`, a `why` note, and a preliminary rank.
3. **Resolve** — deterministic: geocode each place (Nominatim), enrich opening hours and
   duration via the resolver chain (Section 9), drop-and-backfill hallucinations.
4. **Rank** — user reviews candidates (colored by category), inspects details, and sets
   their own ratings. `interest_score = blend(user_rating, llm_rank)`, user rating dominant.
   (Auto-rank is the default/non-interactive path used by tests.)
5. **Schedule** — deterministic: anchor-aware clustering → day assignment → per-day route
   ordering → constraint validation → explanation (Section 8).
6. **Review & refine** — user reads the itinerary + the map + the explanations, then:
   - tweaks **geometry levers** (free, instant re-solve), or
   - **locks** good parts and **regenerates** a day/slot with structured + free-text feedback
     (metered LLM call), or
   - reverts to a previous **version**.
7. **Finalize** — optional "Generate real routes" button fetches street polylines + exact
   segment times for the chosen legs and re-validates timing (Section 7).

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
- **CLI is a client of the API**, not a separate code path. NiceGUI (built on FastAPI)
  slots onto the same API in v2.
- **Adapters are cached and swappable** — enables deterministic tests, offline fallback,
  and clean upgrades (e.g. Nominatim → Google Places later).

**Tech:** Python 3.11+, FastAPI + uvicorn, Pydantic v2 (schemas/validation), `pytest`,
`gemini-2.0-flash-lite` default model, NiceGUI + Leaflet (v2 UI).

### 5.1 Persistence & State

Decided at strategy level here (it shapes M0); exact schemas/eviction/rotation defer to the
milestone task-breakdown. **No server database** — that would reintroduce the hosted
dependency we ruled out.

| What | Store | Why |
|---|---|---|
| App state — `trip.yaml`, rankings, locks, **itinerary versions** | **Files** in a per-trip directory (`trip.yaml` + numbered JSON version snapshots) | Human-readable, git-diffable, trivially testable, matches "runs locally"; version history = revert by snapshot |
| Response cache — LLM / geocode / hours / routing | **SQLite** (stdlib, single file) | Keyed lookups + TTL + hit-rate queries; still local/no-server; powers deterministic tests + offline fallback |
| Diagnostics logs | **JSONL files** (Section 13.2) | Greppable, standard, simple; load into SQLite/DuckDB *ad hoc* for analysis — do **not** build a logging DB |

A DB for app state (or Postgres anywhere) earns its place only with cross-trip queries,
concurrency, or multi-user — all out of scope for v1.

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
> gracefully (Section 11), never hard-fail on quota.

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
5. **Explain** every non-trivial decision (Section 8.4).

### 8.2 Objective function (soft)
```
score =  w_interest · Σ(interest_score)
       − w_travel   · (total_travel_time + inter_cluster_penalty)
       − w_pace     · (overpacking_penalty)
```
Defaults encode the user's ranking: **interest > travel > pace**
(e.g. `w_interest 0.5 / w_travel 0.3 / w_pace 0.2`).

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
- Pace within the user's stops/day preference.

**Soft (optimized, configurable):**
- Meal slots (lunch/dinner; optionally coffee/dessert as a preference).
- Time-of-day affinity (viewpoints→sunset, markets→morning, nightlife→night).
- Fatigue pacing (don't stack heavy stops; gentle day-1 if late arrival).
- Weather (rain demotes outdoor, promotes indoor — Open-Meteo).

**Must-sees** are *near-hard*: try to **move** to a day that fits; if impossible, **drop**
and **surface the reason** to the user. Never silently swallowed.

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
calls at fixed pipeline stages.**

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
- Pace within preference.
- Every dropped place has a logged reason; every must-see is scheduled **or** surfaced as
  un-fittable with a reason.

**LLM-layer tests:** recorded/cached responses (VCR-style) so they're deterministic;
schema-validation tests; a hallucination test (feed a non-geocoding place → assert
drop-and-backfill).

**Quality:** judged by the user via the refine loop. **LLM-as-judge eval is out of scope.**
Golden-output tests only for pure-deterministic transforms (clustering, route ordering).

### 13.2 Diagnostics logging (hard requirement)
Structured logs (JSON lines) capturing: every external call (service, latency, cache hit,
quota state), every resolver decision (`source` + `confidence`), every scheduler
drop/move/penalty with reason, hallucination drop rate, and per-run LLM call count.
Human-readable reasons are surfaced in the itinerary (Section 8.4); machine detail goes to
the log.

### 13.3 Performance
- Geometry re-solve (lever change): **sub-second**, no network.
- Baseline plan: bounded by 1 LLM call + 1–2 matrix calls + cached geocoding.

### 13.4 Documentation (hard requirement)
- **README** — setup, obtaining a Gemini key, running the CLI, configuring `trip.yaml`.
- **`trip.yaml` reference + worked example** (Section 12 is the seed).
- **API docs** — FastAPI's auto-generated OpenAPI/Swagger, kept accurate via Pydantic schemas.
- **Code docstrings** on engine modules; the **LLM↔scheduler contract** (Section 3.2) and the
  **anchor model** (Section 3.1) documented as the load-bearing concepts.
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

## 16. Milestones

- **M0 — Skeleton:** package layout, Pydantic schemas, `trip.yaml` loader, per-trip file
  store + version snapshots, SQLite response cache, JSONL diagnostics logger, adapter
  interfaces, CI with invariant-test harness.
- **M1 — Engine core (deterministic):** anchors, clustering, two-tier travel, scheduler,
  constraints, move-then-drop, explainer. Haversine travel. Full invariant tests.
- **M2 — Curation + resolution:** Gemini Curator (batched, structured), Nominatim geocode,
  hours/duration resolvers, drop-and-backfill, failure handling, deterministic fallback.
- **M3 — FastAPI + CLI:** expose engine; interactive + auto rank; Markdown + JSON output.
- **M4 — Real travel + weather:** ORS matrix, on-demand polylines + re-validation, Open-Meteo.
- **M5 — Refinement loop:** geometry levers (free), content regen (metered), locks, versioning.
- **M6 — NiceGUI UI:** map (colored/numbered by day), rating pane, drag-reorder, levers,
  feedback, history.

v1 = M0–M5 (engine + API + CLI, fully tested). v2 = M6 (UI).

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
- Concrete pace → stops/day mapping (e.g. relaxed 3–4, balanced 5, packed 6–7) — tune in M1.
- Whether per-slot regeneration is needed in v1 or per-day suffices (start per-day).
- Default candidate over-fetch count per category (start ~8).
