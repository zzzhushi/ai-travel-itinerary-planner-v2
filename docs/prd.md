# PRD: AI Travel Itinerary Planner
Status: approved   ·   Date: 2026-06-12   ·   Mode: project   ·   Type: product

## Problem

Someone landing in an unfamiliar city for a few days struggles to turn their interests into a realistic day-by-day plan. The hard part isn't finding things to do — it's sequencing them so a day doesn't criss-cross the city, respects opening hours and any fixed commitments, and leaves time to actually enjoy each stop. Doing this by hand means juggling a map, opening hours, and travel times across a dozen browser tabs.

## Users

A traveller planning their own trip to a single city for a few days. Plans for themselves (no agency/multi-client use). Comfortable running a local tool and supplying their own API keys. Group-type personalization (kids/couple) is **out of scope for v1** (see Non-goals) but designed to be addable later.

## Goals & success criteria

The product works if, for a real upcoming trip, it:

1. Produces a day-by-day schedule where **each day stays geographically compact** (no avoidable criss-crossing) and **starts/ends near the user's lodging**.
2. **Never schedules a place outside its opening hours** when hours are known, **always honors fixed-time commitments**, and **visibly flags** places whose hours are unverified.
3. **Guarantees every "must-see" (5-rated) place is included**, or — if they can't all fit — **says so up front with concrete numbers** and asks the user to re-prioritize before building.
4. Uses **real, currently-existing places** (not hallucinated), with enough trust that the user doesn't feel they must re-verify every suggestion exists.
5. Lets the user **refine the plan in natural language** ("make day 2 more hands-on") and get a revised plan that still obeys every hard constraint.
6. Is **faster and less frustrating than planning by hand** — the standing success test is "would the user actually use this for their next trip instead of browser tabs?"

These are the acceptance themes; each milestone turns the relevant ones into specific tests.

## Non-goals (v1)

- **Day trips / out-of-city destinations** — deferred to v2 (requires real routing; haversine can't model inter-town travel). v1 is strictly intra-city.
- **Multi-city trips** — v2+.
- **Real/transit-aware routing** — v1 uses haversine (straight-line) travel time; Google Routes API is a v2 upgrade.
- **LLM-generated prose / day narrative** — the day view is rendered **deterministically** (what the day is about + the stops and times); no LLM narration call.
- **Group-type personalization** (kid-friendly/couple bias) — additive later (a trip attribute + a curation signal + minor scheduler tweaks); not v1.
- **Accounts / multi-user / hosting** — single local user, no auth.
- **Booking or reservations** — the tool plans; it never books anything.
- **Offline operation** — fresh place data requires internet; "local" means runs-on-your-machine, not network-free.
- **Local LLM in v1** — Gemini to start; a pluggable local model is a designed-for *future* option, not built in v1.

## Delivery note

v1 is a substantial scope (web app, map, free-text interests, feedback loop, versioning). It is delivered in **vertical slices, engine-first**: scaffolding → a thin routing-engine slice (single day, must-sees only) → real place data → web shell → map → feedback → versioning. "In v1" denotes the eventual product, not milestone 1. The `/milestones` stage owns that sequencing.

## Core flows

1. **Create a trip.** User provides: city; dates; arrival time (day 1) and departure time (last day); lodging location; the **interests** to activate for this trip (drawn from their reusable interest library, or newly added); pace; whether to plan meals; filters (budget, dietary, accessibility — each hard or soft) and soft knobs (walking tolerance); and any **fixed-time anchors** (e.g. "museum ticket Tue 10:00", "dinner Fri 19:00").
2. **Get & rate suggestions.** For each active free-text interest, the tool fetches real candidate places (text search → structured coords/hours), and the LLM **filters them for genuine fit** to the interest's nuance and adds a one-line description — it does **not** score them. The **user rates each candidate 1–5** (1 = low interest, 5 = must-do; low/unrated ≈ skip).
3. **Feasibility check (deterministic) + pushback.** Before building, the tool estimates capacity (available days × usable hours ÷ average time-per-place incl. travel) vs. the high-priority picks, and checks anchor compatibility. If over-committed, or a chosen place is closed on every available day, or two anchors are mutually infeasible, it reports specifics and asks the user to trim/re-rank/swap. No LLM call until feasible.
4. **Build schedule (deterministic).** The engine clusters places into days by geography (anchored to lodging), then solves each day as a **Traveling Salesman Problem with Time Windows** — respecting opening hours, visit durations, the daily time budget (pace), partial first/last days, optional meal windows, walking tolerance, and **fixed anchors as hard time windows**.
5. **Refine (LLM + engine).** The user gives natural-language feedback. The LLM proposes **what to change** — place add/remove/**swaps**, rating changes, parameter changes, soft preferences — as a structured *sketch*, and the deterministic engine **re-solves** from it. The LLM never emits clock times; anchors and hours remain hard, so a revision can't violate them.
6. **View & export.** Web app: a **deterministically rendered** day view (each day's theme, stops, and times) plus an **interactive map** (markers + day routes). Export an itinerary to Markdown and optionally a static map image for sharing/printing.
7. **Save, version & reopen.** Trips persist (inputs, ratings, place IDs). The tool keeps the **last 3 schedule versions**, revertible after a refinement. Reopening re-fetches live place details (hours/coords) — requires internet.

## Requirements

**Interests, suggestions & ranking**
- Interests are **free-text prompts**, optionally category-grouped, owned by the user as a **reusable library that grows across trips**; each trip **activates a subset** (keep the active set modest — it bounds both ranking effort and Places quota).
- Per active interest: LLM generates the place text-search query (batched across interests in one call), then **filters candidates for fit** to the interest's nuance (chunked across interests to respect output limits). Cap candidates per interest; **dedupe places shared across interests**; cache by `place_id`.
- **The user does the 1–5 ranking.** The LLM never assigns the score. Rating drives scheduling priority; 5 = must-include.

**Filters & preferences**
- **Budget, dietary, accessibility** — each settable as a **hard constraint** (excludes options) or a **soft preference** (skews scoring). Accessibility as a hard need also biases the scheduler toward compact, low-walking days.
- **Pace** and **walking tolerance** — soft scheduler knobs feeding the day budget and travel weighting.
- Richer soft taste (vibe, hidden-gem-vs-popular, indoor lean) is expressed through free-text interests + ratings, not additional toggles.

**Scheduling (deterministic core)**
- Cluster into days by geography; anchor each day's start/end near lodging.
- Solve each day as **TSPTW**: opening hours and meal slots as time windows, fixed anchors as hard (tight) windows, per-place visit durations, daily time budget from pace, partial first/last days, travel time = haversine ÷ per-mode assumed speed, configurable slack/buffers.
- Must be runnable and unit-testable **without the LLM**. (Solver choice — Google OR-Tools routing vs. an insertion-heuristic + local-search fallback — is an architecture-gate decision; the TSPTW framing is fixed.)

**Feasibility & pushback**
- Deterministic capacity + anchor-compatibility check before building; report infeasibility with numbers and request re-prioritization. Never silently emit a bad plan.

**Refinement loop**
- LLM converts natural-language feedback into a structured **sketch** (selection/order/soft-prefs/param/rating deltas, especially swaps); the deterministic engine re-solves. The LLM never produces clock times. Hard constraints (anchors, hours) are inviolable across refinements.

**Presentation**
- The day-by-day view is **rendered deterministically** from schedule data (theme/area label, ordered stops, times, travel legs, "hours unverified" flags). No LLM in the view path.

**Failure behavior / degradation**
- Unknown opening hours → assume a sensible per-category default **and flag the place "hours unverified."**
- External API failure or free-tier quota hit → retry with backoff → fall back to OSM for place data where possible → if all sources fail, stop with a clear, logged, correlation-id'd error plus any partial results.

**Persistence & versioning**
- Save trips: user inputs, ratings, and place IDs. Keep the **last 3 schedule versions** (revertible). Re-fetch live details (coords/hours) on reopen; do **not** durably store coordinates beyond the source's caching window (see ADR-001).

**Map**
- Web app shows an **interactive map** (pan/zoom/click markers, toggle days). The map provider is **pluggable behind an interface**: free OSM tiles (Leaflet/MapLibre) is the v1 default; a Google Maps JS implementation can be swapped in later for testing.

**Observability & quality (per docs/engineering-standards.md)**
- Diagnostics sufficient to trace a failed itinerary build end-to-end from telemetry alone, correlated across suggestion → feasibility → schedule → refinement and every external call. OpenTelemetry tracing/spans leaning.
- **Telemetry lives outside the persistence DB:** spans export to a tracing backend (console/file in dev, optional local Jaeger); structlog logs carry the `trace_id` for correlation; the DB holds only domain data. A "spans table" in the app DB is explicitly rejected (reinvents a tracing store).
- Automated tests, with the deterministic scheduler covered directly.

**LLM usage & cost control**
- LLM touchpoints (no narration): (1) interpret interests → search queries (one batched call), (2) fit-filter candidates (chunked by interest), (3) one *sketch* call per refinement round. Feasibility, scheduling, and the day view are deterministic.
- Curation scales with the count of **active** interests, so the binding cost pressure is the **Places API quota**, mitigated by candidate caps, `place_id` caching/dedup, and modest per-trip activation. Gemini's daily request cap is not the constraint.
- Calls are structured-in / structured-out at low temperature; the refinement prompt is explicitly forbidden from emitting a schedule. **Output token cap (and large-batch quality loss) is what forces chunking** — verify the model's output limit. Exact prompts are implementation-stage.
- Stay within free-tier caps; a spend guard prevents runaway cost; warn/degrade before anything would bill.

## Data entities

- **Trip** — city, date range, arrival/departure times, lodging, pace, walking tolerance, meal toggle, filters (each with hard/soft mode), activated interests, status.
- **Interest** — a free-text prompt, optional coarse category; **user-owned and reusable across trips** (a library).
- **Place** — a real POI: place id (durable), name, category, and *cached* details (coordinates, opening hours, rating, price level) treated as refreshable.
- **RankedPlace** — a Place within a Trip with the user's 1–5 rating and the interest it answered.
- **FixedAnchor** — a user commitment with a day and/or exact time window.
- **Lodging** — the trip's anchor location.
- **ScheduledStop** — a Place placed on a Day at a start/end time, with travel-from-previous.
- **Day** — ordered ScheduledStops for one date, with a deterministic theme/area label.
- **ScheduleVersion** — a full routed itinerary (Days + feasibility report); up to 3 retained per Trip, revertible.

## External integrations

Final selection of specific services is ratified at the `/milestones` architecture gate; the **needs** are fixed here.

- **LLM** — **Gemini** (hard constraint). Interest→query generation, candidate fit-filtering, refinement-sketch generation. Pluggable so a local model can replace it later.
- **Place data (source of truth)** — a service providing structured coordinates + opening hours + rating/price with good freshness. **Leading choice: Google Places API (New); see ADR-001.** Requires a Google Cloud billing account + key even on free tier.
- **Place-data fallback** — **OSM / Overpass** (free, cache-friendly license) for degradation and as the one source whose data may be durably cached.
- **Travel time** — v1: local haversine computation (no API). v2: Google Routes API.
- **Map tiles** — v1: free **OpenStreetMap** tiles (no key, no per-load billing); pluggable to Google Maps JS later.

## Hard constraints

- Runs **locally** (web app on the user's machine, no hosted backend); internet allowed and required for fresh data.
- **Python** (web frontend tech TBD at architecture gate).
- LLM is **Gemini** to start; designed to swap to a local model later.
- **Automated tests** required; **diagnostics/observability** required (traceable build).
- **Cost ceiling: free-tier only (~$0)** with a spend guard; degrade/warn before billing; free map tiles by default.

## Open questions

- **Scheduler solver:** Google OR-Tools routing (TSPTW) vs. a hand-rolled insertion-heuristic + local-search fallback. Architecture gate.
- **Persistence DB:** SQLite is the leaning default (local, file-based, single-user, bounded data); architecture gate.
- **Observability stack:** OpenTelemetry tracing (spans per stage + per external call), logs correlated by `trace_id`, exported to a trace store/file (console/file dev; optional local Jaeger) — **separate from the persistence DB**. Architecture gate.
- **Web framework / map library:** backend (e.g. FastAPI) and map lib (Leaflet vs. MapLibre). Architecture gate.
- **Active-interest cap & candidates-per-interest cap** — concrete numbers, to bound ranking effort and Places quota.
- **Default visit durations** per category — concrete starting numbers needed.
- **Pricing verification (blocking before build):** confirm 2026 free-tier coverage for Gemini (daily request cap + output token limit), Google Places Details, and the Google Maps Platform free tier; confirm OSM-tile usage policy. Feeds ADR-001.

## Decisions log

Forks with a real alternative are linked to ADRs; architecture-level decisions are flagged for ratification as ADRs at the `/milestones` gate.

| Decision | Choice | Why / note |
|---|---|---|
| Meaning of "runs locally" | Local web app, external APIs allowed; not offline | User wants most-current info on what to do |
| Place data source | Structured place API as source of truth; LLM curates | LLM alone hallucinates; grounding lacks structured coords/hours → [ADR-001](decisions/001-place-data-source.md) |
| Travel-time model (v1) | Haversine ÷ assumed speed | Free, good enough intra-city; real routing deferred → architecture-gate ADR |
| Schedule production | Deterministic engine produces all times/ordering; LLM never authors times | Preserves no-criss-cross/hours/anchor guarantees, reproducible, testable → architecture-gate ADR |
| Scheduling algorithm | Per-day TSP with Time Windows; anchors = hard windows | Correct problem model; OR-Tools the leading solver → architecture-gate ADR |
| Feedback loop | LLM emits a *sketch* (swaps/selection/soft-prefs/deltas); engine re-solves | **Confirmed.** Option-2 flexibility without losing validity; LLM can't violate anchors (emits no times) |
| Interests | Free-text prompts; reusable library + per-trip activation | "food" too blunt; library matches "built up over time"; activation bounds quota |
| Ranking | **User** assigns 1–5; LLM only filters candidates for fit | User-directed; keeps LLM out of preference scoring |
| Day narrative | None; deterministic day view | User doesn't want it; saves LLM calls |
| Pace | Per-trip knob, default balanced | Different travellers, same city |
| Walking tolerance | Soft scheduler knob | Sibling to pace; soft form of accessibility |
| Filters (v1) | Budget, dietary, accessibility — each hard or soft | Hard = exclude, soft = skew; richer taste via free-text + ratings |
| Meals | Optional per-trip toggle; meal windows + food picks | Food is a named interest; some wing it |
| Fixed anchors | Supported in v1 as hard time windows | Most common real constraint; central to scheduler |
| Lodging anchor | One lodging; days radiate from it | Avoids stranding across town |
| Partial days | Arrival/departure shrink day 1 / last day | Prevents over-packing |
| Day trips | Deferred to v2 | Conflicts with haversine; keep v1 lean |
| Interface | Local web app in v1; headless engine is the tested core | User wants web + map; engine tested independently of UI |
| Maps | Interactive, free OSM tiles; pluggable to Google Maps JS later | Free by default; second impl genuinely planned → interface seam |
| Persistence | Save inputs + ratings + place IDs; re-fetch on open | Caching policy forbids storing coords durably → [ADR-001](decisions/001-place-data-source.md) |
| Versioning | Keep last 3 schedule versions, revertible | Cheap (schedule is data); pairs with refinement loop |
| Telemetry storage | Traces to a tracing backend (file/Jaeger), **not** the app DB | Different shape/lifecycle; a spans table reinvents a tracing store badly |
| Persistence DB | SQLite leaning | Architecture-gate ADR |
| Cost ceiling | Free-tier only with spend guard; free map tiles | Hobby use; user is the key operator |
| Missing hours | Default per category + flag "unverified" | Keeps good places in without faking certainty |
| API failure | Retry → OSM fallback → clear logged error + partials | Honors free-tier ceiling + diagnostics goal |

### Assumptions flagged for ratification
- **Place source = Google Places (New):** leading choice, ratified at architecture gate after pricing verification.
- **Free-tier sufficiency:** assumed adequate; verify against live 2026 pricing (incl. Gemini output-token limit) before build.
- **Caps (active interests, candidates per interest):** to be set with concrete numbers before the suggestion flow is built.
