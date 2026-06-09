# Architecture — AI Travel Itinerary Planner

How the code is structured and why. Pairs with the requirements in [PRD.md](../PRD.md), the
glossary in [CONTEXT.md](../../CONTEXT.md), and the decisions in [docs/adr/](../adr/).

---

## 1. Principles

- **The core is pure and UI-agnostic.** `planner/` contains all domain logic and imports
  *nothing* from an adapter. Adapters (CLI now, FastAPI later) depend on the core, never the
  reverse ([ADR-0002](../adr/0002-ui-agnostic-core-cli-first.md)).
- **External effects sit behind interfaces.** LLMs, geocoding, routing, search, persistence,
  and telemetry are all `Protocol`s with real + fake implementations, so the core is testable
  with no network ([ADR-0001](../adr/0001-tiered-geo-sourcing.md), [ADR-0006](../adr/0006-llm-provider-abstraction-fallback-chain.md)).
- **Determinism where it counts.** Domain logic (capacity, dedupe, validator) is deterministic
  and unit-tested; LLM scheduling is non-deterministic and checked by the validator
  ([ADR-0005](../adr/0005-deterministic-travel-aware-scheduler.md)).
- **Dependency direction:** `adapters → services → {providers, repository, domain}`; `domain`
  depends on nothing.

---

## 2. Package layout

```
ai-travel-itinerary-planner-v2/
├── CONTEXT.md                       # glossary
├── docs/{PRD.md, ARCHITECTURE.md, adr/}
├── pyproject.toml                   # deps + tool config (ruff, pytest, mypy)
├── .env.example                     # keys, POSTGRES_DSN, provider chain
├── planner/                         # ── the UI-agnostic core ──
│   ├── domain/                      # entities + value objects (no I/O)
│   │   ├── models.py                # Trip, Category, Interest, Option, Schedule, ScheduleItem
│   │   ├── enums.py                 # Pace, TransportMode, GeoSource, Category defaults
│   │   └── errors.py                # InfeasibleConstraint, ProviderExhausted, ...
│   ├── services/                    # use-cases = the pipeline steps
│   │   ├── trip_setup.py            # create Trip, default Categories, add Interests
│   │   ├── gathering.py             # gather Options (LLM, per-Category batch, cache, dedupe)
│   │   ├── geocoding.py             # resolve Option locations + build travel matrix
│   │   ├── rating.py                # apply Ratings, derive Chosen set
│   │   ├── capacity.py              # Capacity math + over/undersupply gate
│   │   └── scheduling.py            # build prompt, call LLM, run validator, re-prompt
│   ├── providers/                   # ── effectful interfaces + impls ──
│   │   ├── llm/                     # LLMProvider Protocol; gemini, groq, openrouter, ollama; chain.py
│   │   ├── geo/                     # GeoProvider + TravelProvider; google, osm, llm_estimate; tiered.py
│   │   ├── search/                  # SearchProvider Protocol (optional grounding) — Phase 2
│   │   └── cache.py                 # (city, interest) gather cache; geocode cache
│   ├── scheduling/                  # pure scheduling helpers
│   │   ├── prompt.py                # render Options + matrix + constraints into a prompt
│   │   └── validator.py            # deterministic checks + score (hours/window/meal/zig-zag)
│   ├── repository/                  # persistence interface + impl
│   │   ├── interface.py             # Repository Protocol
│   │   ├── sqlite_repo.py           # SQLite implementation (file or :memory:)
│   │   └── schema.sql               # domain DDL
│   ├── telemetry/                   # OTel setup + custom Postgres exporter
│   │   ├── otel.py                  # tracer/span helpers; trace_id == request_id
│   │   └── pg_exporter.py           # SpanProcessor/exporter → Postgres (log_event, llm_call)
│   └── config.py                    # pydantic-settings; reads .env
├── planner_cli/                     # ── adapter #1: CLI (Typer) ──
│   └── main.py                      # commands: trip / gather / rate / capacity / schedule / show
└── tests/
    ├── fakes/                       # FakeLLMProvider, FakeGeoProvider, in-memory repo
    ├── unit/                        # validator, capacity, dedupe, rating, repository
    ├── property/                    # Hypothesis invariants on the validator
    ├── integration/                 # full pipeline with fakes
    └── cassettes/                   # recorded real payloads (schema-drift checks)
```

---

## 3. Module responsibilities

| Module | Responsibility | Depends on |
|--------|----------------|------------|
| `domain/` | Data shapes + invariants; no I/O | — |
| `services/*` | One pipeline step each; orchestrate providers + repository | domain, providers, repository, telemetry |
| `providers/llm/*` | Generate/gather/schedule via a model; fallback chain | domain, config |
| `providers/geo/*` | Geocode + travel matrix via tiers | domain, config |
| `scheduling/validator.py` | Deterministic Schedule scoring + checks | domain |
| `scheduling/prompt.py` | Serialise inputs to an LLM prompt | domain |
| `repository/*` | Persist/load Trip state | domain |
| `telemetry/*` | Tracing + Postgres log/token export | config |
| `planner_cli/` | Map commands ↔ services; render output | services |

---

## 4. Domain model (pydantic)

```python
class Pace(StrEnum):        RELAXED; BALANCED; PACKED          # → slots/day (OQ-3)
class TransportMode(StrEnum): WALK; TRANSIT; DRIVE             # → which travel matrix
class GeoSource(StrEnum):   GOOGLE; OSM; LLM_ESTIMATE          # provenance (ADR-0001)

class Trip(BaseModel):
    id: TripId; city: str; arrival_at: datetime; num_days: int
    pace: Pace; daily_start: time; daily_end: time; transport_mode: TransportMode
    home_base: LatLng | None                                   # lodging; day start/end anchor (ADR-0007)
    pins: list[PinnedCommitment]                               # fixed time+place items (ADR-0007)
    prefs: dict                                                # free-form extras
    categories: list[Category]

class PinnedCommitment(BaseModel):                             # wedding | locked ticket | flight
    id; title; lat: float; lng: float
    start: datetime; end: datetime | None                      # OQ-7: end optional
    kind: str                                                  # "event" | "ticket" | "flight"
    # immovable: the scheduler places it exactly; regeneration never moves it; validator asserts so

class Category(BaseModel):  id; name; interests: list[Interest]
class Interest(BaseModel):  id; text; options: list[Option]
class Option(BaseModel):
    id; name; description; address
    source: str                                               # "llm" | "user" (user-added place)
    lat: float | None; lng: float | None; geo_source: GeoSource | None
    opening_hours: OpeningHours | None
    est_visit_minutes: int                                    # LLM/category estimate (wait-time aware)
    user_visit_minutes: int | None                            # override; precedence user > LLM > category default
    image_ref: str | None                                     # photo reference / public URL (P2 UI)
    rating: int | None                                        # 1..5; <3 excluded
    gather_provider: str | None; gather_request_id: str | None

    @property
    def chosen(self) -> bool: return (self.rating or 0) >= 3   # Chosen = rated ≥ 3
    @property
    def visit_minutes(self) -> int: return self.user_visit_minutes or self.est_visit_minutes

class ScheduleItem(BaseModel):
    day_index: int; order_in_day: int; option_id; start: time; end: time
    travel_minutes_from_prev: int
class Schedule(BaseModel):  id; trip_id; items: list[ScheduleItem]; created_at; params: dict
```

---

## 5. Key interfaces (Protocols)

```python
# providers/llm/interface.py
class LLMProvider(Protocol):
    name: str
    def gather_options(self, city: str, interest: str, n: int) -> list[Option]: ...
    def schedule(self, ctx: ScheduleContext) -> Schedule: ...   # ctx carries Chosen + travel matrix + constraints

# providers/llm/chain.py — tries providers in order; on quota/rate-limit error, falls to next (ADR-0006)
class LLMChain(LLMProvider): providers: list[LLMProvider]

# providers/geo/interface.py
class GeoProvider(Protocol):
    def geocode(self, name: str, address: str | None, city: str) -> GeoResult | None: ...  # sets GeoSource
class TravelProvider(Protocol):
    def matrix(self, points: list[LatLng], mode: TransportMode) -> TravelMatrix: ...
# tiered.py composes Google → OSM → LLM-estimate (geocode) and Google DistanceMatrix → OSRM → haversine (travel)

# providers/search/interface.py  (Phase 2, optional grounding for non-Gemini models)
class SearchProvider(Protocol):
    def find_places(self, query: str, city: str) -> list[PlaceHint]: ...

# repository/interface.py
class Repository(Protocol):
    def save_trip(self, trip: Trip) -> None: ...
    def load_trip(self, trip_id: TripId) -> Trip: ...
    def save_schedule(self, s: Schedule) -> None: ...

# scheduling/validator.py
class ScheduleValidator:
    def check(self, schedule: Schedule, trip: Trip, matrix: TravelMatrix) -> ValidationReport: ...
    # report: hours_violations, window_overflow, meal_misfit, per_day_travel, zigzag_flag, score
```

---

## 6. Persistence

**Domain state — SQLite** (`repository/schema.sql`), tables: `trip`, `category`, `interest`,
`option`, `schedule`, `schedule_item` — columns per the model in §4. `:memory:` in tests
([ADR-0004](../adr/0004-sqlite-state-postgres-logs.md)).

**Telemetry — Postgres** (`telemetry/pg_exporter.py`):
```sql
log_event(id, ts, level, request_id, trip_id, component, message, payload_jsonb, latency_ms)
llm_call(id, ts, request_id, trip_id, provider, model, prompt_tokens, completion_tokens,
         latency_ms, cache_hit)
```
`request_id` = OTel `trace_id`. Correlate any run: `WHERE request_id = '...'`
([ADR-0003](../adr/0003-otel-with-postgres-exporter.md)).

---

## 7. Data flow (the pipeline)

```
trip_setup ─▶ gathering ─▶ geocoding ─▶ rating ─▶ capacity ─▶ scheduling ─▶ (render)
  (A1/A2)    (B1: LLM+    (B2: tiers+   (C1)      (C2 gate)   (D1 LLM +       (D3)
             cache+dedupe) matrix)                            D2 validator
                                                              + capped reprompt)
```
Each arrow is a `services/*` function; each runs inside an OTel span carrying the request id.
Only **Chosen** Options enter `geocoding`'s matrix build and `scheduling` — keeping tokens and
geo calls minimal (NFR-002).

---

## 8. Configuration (`config.py`, pydantic-settings ← `.env`)

```
LLM_CHAIN=gemini,groq,ollama          # ordered fallback (ADR-0006)
GEMINI_API_KEY=...  GROQ_API_KEY=...  OPENROUTER_API_KEY=...
OLLAMA_HOST=http://localhost:11434  OLLAMA_MODEL=qwen2.5
GOOGLE_MAPS_API_KEY=...                # optional; absent ⇒ OSM tier
POSTGRES_DSN=postgresql://...          # telemetry sink; absent ⇒ console exporter
OTEL_ENABLED=true
GATHER_OPTIONS_N=...                   # OQ-2    SCHEDULER_MAX_REPROMPTS=...  # OQ-4
ZIGZAG_THRESHOLD_MIN_PER_DAY=...       # OQ-1    SLOTS_PER_PACE={relaxed:3,...} # OQ-3
```
Secrets are never written to logs (telemetry redacts key fields).

---

## 9. Error handling & fallback

- `ProviderExhausted` (quota/rate-limit) → `LLMChain` advances to the next provider; if all
  fail, surface a clear message naming the chain tried.
- `InfeasibleConstraint` (e.g. a force-included Option open only on an absent day) → surfaced
  to the user pre-schedule, not silently dropped (FR-014).
- LLM JSON parse failure → one repair retry, then skip the offending record and log it.
- Validator hard-fail → re-prompt up to `SCHEDULER_MAX_REPROMPTS`, then return best-effort
  Schedule flagged with its `ValidationReport`.

---

## 10. Testing structure (default run = no network)

| Layer | What | Tooling |
|-------|------|---------|
| `unit/` | validator, capacity, dedupe, rating, repository (`:memory:`) | pytest |
| `property/` | validator invariants over random Options/constraints | Hypothesis |
| `integration/` | full pipeline with `FakeLLMProvider` + `FakeGeoProvider` | pytest |
| `cassettes/` | a few recorded real payloads to catch schema drift | pytest + recorded JSON |
| live (gated) | real Gemini/Maps behind an env flag; never in default CI | pytest marker |

---

## 11. CLI surface (`planner_cli`, adapter #1)

```
planner trip new        # A1/A2 setup → returns trip_id (+ request id)
planner gather TRIP      # B1+B2: gather Options, geocode
planner rate TRIP        # C1: assign Ratings
planner capacity TRIP    # C2: show the gate verdict
planner schedule TRIP    # D1+D2: generate + validate (+ reprompt)
planner show TRIP        # D3: render Schedule with travel times
```
Phase 2 replaces this adapter's role with a FastAPI app over the same `services/*`, returning
`trace_id` as the `X-Request-ID` header.

---

## 12. Future seams (planned, not built — see PRD "Future Requirements & Triage")

Where each deferred feature plugs in, so adding it isn't a rewrite:

- **Pinned Commitments (wedding / locked ticket / flight)** — `Trip.pins`; the scheduler's
  input contract accepts them now; `scheduling/validator.py` gains "pin at exact time + unmoved
  on regen". Locking a scheduled Option = creating a pin at its current time ([ADR-0007](../adr/0007-anchors-and-anchor-aware-scheduling.md)).
- **Home Base (MVP)** — `Trip.home_base`; `services/scheduling.py` routes each day
  home_base → … → home_base; validator checks day start/end.
- **Anchor-aware clustering** — a heuristic in `scheduling/prompt.py` + scoring in
  `validator.py`: prefer nearby Options in slots adjacent to an Anchor.
- **Buffer** — config (global/per-pace) + optional per-Option; enforced in prompt + validator
  (deterministic, not LLM-invented). *OQ-6.*
- **User-added Options** — `Option.source="user"`; reuse `geocoding.py` to resolve text →
  `place_id`/coords/Maps link.
- **Per-Option duration** — `Option.visit_minutes` precedence already in the model.
- **Images** — `Option.image_ref`; a `providers/images/` provider (Google photo ref via API,
  or Wikimedia). *OQ-9.*
- **Map UI** — pure frontend over existing coords/category/day_index (P2).
- **Multiple trips** — already independent by id; add `Repository.list_trips()` + CLI `trip list`.
- **Multi-city** — reshape `Trip` → `list[CityStay]` (city + dates + Home Base) joined by
  inter-city transport; flights become inter-stay transfers.
- **Non-technical packaging** — an `init` setup wizard, default to local Ollama, optional JSON
  `Repository` impl, packaged executable, per-OS docs. Documented goal; deferred.
