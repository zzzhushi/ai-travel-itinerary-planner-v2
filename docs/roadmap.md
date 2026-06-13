# Roadmap: AI Travel Itinerary Planner
PRD: docs/prd.md (approved) · Architecture: docs/decisions/ ADR-001…006 · API: docs/api-contract.md
Status: draft (awaiting slicing approval) · Date: 2026-06-12

## Principles applied

- **Vertical slices, engine-first.** Each milestone ends in a runnable, judgeable demo. The riskiest assumption (can a deterministic heuristic route well?) is retired first, on fixtures, before any network.
- **API and UI accrete per use-case.** Each milestone exposes its operation through a CLI command *and* a thin FastAPI endpoint (api-contract.md). The htmx **UI accretes from M4** — the point a persisted, interactive app first exists; M1–M3 are CLI/curl-driven (a UI over fixture-only engine adds nothing). Only the **map (M8)** is a dedicated feature slice.
- **Complexity → model** (workers never self-assess): mechanical → haiku, standard → sonnet, complex → opus. A task is rated below `complex` only if its failing test can be written first.

## Milestone overview

| # | Issue | Demo sentence | Retires risk | tasks |
|---|---|---|---|---|
| 0 | [#2](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/2) | `python run_cli.py --version` and `GET /health` run green through CI; one log line carries the full trace schema | foundation + observability | 8 |
| 1 | [#3](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/3) | `schedule oneday.json` (and `POST /schedule`) → a routed **single day** respecting hours, durations, day window, lodging commute | can the heuristic route at all | 6 |
| 2 | [#4](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/4) | a **multi-day** plan: geo-clustered days, partial first/last days, meal windows, walking tolerance | multi-day quality | 6 |
| 3 | [#5](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/5) | a plan honoring a pinned **7pm dinner**; **feasibility pushback** when over-committed; **re-rank → rebuild** | anchors + infeasibility + re-solve | 7 |
| 4 | [#6](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/6) | create & reopen a trip **in the browser**; revert a version (SQLite + web UI shell) | persistence + UI shell | 9 |
| 5 | [#7](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/7) | `--interest "miradouros"` → **real cached places** shown in the browser (Google→OSM, quota-guarded) | real data + ToS + free-tier | 10 |
| 6 | [#8](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/8) | `--interest "cafés that serve more than coffee"` → **LLM-curated** candidates rated **in the browser**, with `reasoning` | LLM curation | 8 |
| 7 | [#9](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/9) | `refine "make day 2 more relaxed"` **in the browser** → a valid revised version honoring anchors | NL refinement | 6 |
| 8 | [#10](https://github.com/zzzhushi/ai-travel-itinerary-planner-v2/issues/10) | options and the schedule **on a map**, toggle days, static export | the map | 5 |

---

## Milestone 0 — Scaffolding, observability, dual-delivery skeleton
**Demo:** `python run_cli.py --version` prints the version; `GET /health` returns 200; CI is green; a trivial use-case emits one log line carrying every field in the observability schema.
**Exit criteria:**
- [ ] `uv run ruff check && uv run mypy && uv run pytest -q` all pass in CI — proven by the CI run
- [ ] coverage ratchet active (build fails if coverage drops) — proven by CI config + a baseline
- [ ] a log line shows `correlation_id`, `trace_id`, `component`, `operation`, `outcome` — `test_observability_schema`
- [ ] both delivery surfaces boot — `test_cli_version`, `test_health_endpoint`
**Validation:** `python run_cli.py --version` · `uv run uvicorn tripplanner.web.app:app` then `curl localhost:8000/health` · push branch, watch CI.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | uv + pyproject (deps, ruff/mypy/pytest cfg, console script, src layout) | mechanical | haiku | config boilerplate | — |
| 2 | package skeleton (domain/services/application, cli.py, web/app.py, __main__, run_cli.py) | mechanical | haiku | dirs + stubs | 1 |
| 3 | `observability/logging.py` — structlog JSON + stdout/file sinks + schema fields | standard | sonnet | follows standards schema | 2 |
| 4 | `observability/tracing.py` + `context.py` — OTel spans/events + correlation/trip binding | complex | opus | tracing wiring, subtly wrong-able | 3 |
| 5 | pre-commit (ruff + gitleaks) + activate repo hooks | mechanical | haiku | config | 1 |
| 6 | CI workflow: lint, types, tests, coverage ratchet | standard | sonnet | CI yaml + ratchet | 1 |
| 7 | FastAPI app + `/health`; CLI `--version` | standard | sonnet | dual-delivery skeleton | 2 |
| 8 | walking-skeleton use-case + smoke tests (schema, version, health) | standard | sonnet | end-to-end wire | 3,4,7 |

---

## Milestone 1 — Single-day routing engine (fixtures)
**Demo:** `schedule oneday.json` and `POST /trips/{id}/schedule` return a routed single day respecting opening hours, visit durations, the day window (arrival→departure), and the lodging commute legs.
**Exit criteria:**
- [ ] no stop scheduled outside its opening hours — `test_respects_hours`
- [ ] lodging→first and last→lodging travel counted in the day budget — `test_lodging_commute`
- [ ] ordering reduces total travel vs naive input order — `test_reduces_travel`
- [ ] a day that can't fit its stops is reported, not silently truncated — `test_overfull_day_flagged`
**Validation:** `python run_cli.py schedule tests/fixtures/oneday.json` · `curl -XPOST .../schedule` with the fixture trip.
**Architecture note:** `domain/` imports nothing from `services/` (ADR-002); travel lives in `services/travel.py` even though haversine is pure (ADR-003 swap path).

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | domain models (Trip, Lodging, Place, RankedPlace, Day, ScheduledStop, Itinerary) | standard | sonnet | PRD entities | M0 |
| 2 | `durations.py` — category defaults + per-place override | standard | sonnet | simple rules | 1 |
| 3 | `services/travel.py` — haversine duration | mechanical | haiku | known formula | 1 |
| 4 | single-day TSPTW heuristic: order vs hours + durations + day window + commute | complex | opus | core routing algorithm | 1,2,3 |
| 5 | `build_schedule` use-case + CLI `schedule` + `POST /schedule` + deterministic day view | standard | sonnet | wire + presenter | 4 |
| 6 | fixtures + unit tests (hours, commute, ordering, overfull) | complex | opus | correctness test design | 4 |

---

## Milestone 2 — Multi-day engine (fixtures)
**Demo:** `schedule trip.json` → a multi-day plan: places clustered into compact day-areas, day 1 starting at arrival / last day ending at departure, optional meal windows filled, walking tolerance respected.
**Exit criteria:**
- [ ] each day is geographically compact (intra-day spread below a threshold) — `test_days_compact`
- [ ] day 1 / last day honor arrival / departure times — `test_partial_days`
- [ ] meal windows reserved and food picks slotted when enabled — `test_meal_slots`
- [ ] higher walking tolerance permits more spread; lower tightens it — `test_walking_tolerance`
**Validation:** `python run_cli.py schedule tests/fixtures/trip_3day.json`.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | day-clustering: assign places to N days by geography (compact areas) | complex | opus | clustering algorithm | M1 |
| 2 | per-day budgets incl. partial first/last days | standard | sonnet | window math | 1 |
| 3 | meal windows: reserve + slot food picks (optional toggle) | complex | opus | constraint logic | 1 |
| 4 | walking-tolerance weighting into travel cost / compactness | standard | sonnet | param into heuristic | M1 |
| 5 | extend CLI/endpoint output to multi-day | standard | sonnet | presenter | 1 |
| 6 | tests (compactness, partial days, meals, walking tolerance) | complex | opus | correctness | 1,2,3,4 |

---

## Milestone 3 — Anchors, feasibility, rating capture, re-solve (fixtures)
**Demo:** a plan that routes around a pinned 7pm dinner; an over-committed request returns a pushback ("12 must-sees, ~8 fit"); the user re-ranks and rebuilds.
**Exit criteria:**
- [ ] a fixed-time anchor lands at its time and the day routes around it — `test_anchor_honored`
- [ ] mutually infeasible anchors are detected before building — `test_anchor_infeasible`
- [ ] over-commitment returns a 409-style pushback with numbers — `test_feasibility_pushback`
- [ ] a place closed on all available days is surfaced with a swap offer — `test_closed_all_days`
- [ ] editing a rating / swapping a place and rebuilding yields a new result — `test_resolve_after_edit`
**Validation:** `python run_cli.py rate ...` then `schedule`; `curl -XPOST .../schedule` returns 409 with pushback body on the over-committed fixture.
**Architecture note:** the re-solve loop is the pure engine called again with edited inputs — the deterministic core that M7's NL layer drives.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | FixedAnchor model + hard-window placement in the heuristic | complex | opus | tightest constraint | M2 |
| 2 | anchor infeasibility detection | complex | opus | feasibility logic | 1 |
| 3 | capacity feasibility check + closed-on-all-days detection | complex | opus | deterministic check | M2 |
| 4 | templated pushback message (numbers + suggestions) | standard | sonnet | formatting, no LLM | 3 |
| 5 | CLI rating capture (1–5 + duration override) + `PUT /ratings` | standard | sonnet | mimic user input | M2 |
| 6 | deterministic edit + re-solve (rating/param/swap → rebuild) | standard | sonnet | re-run engine | 5 |
| 7 | tests (anchor, infeasible, pushback, closed-all-days, re-solve) | complex | opus | correctness | 1,2,3,6 |

---

## Milestone 4 — Persistence, versioning & web UI shell
**Demo:** create a trip and reopen it **in the browser**; revert to a previous schedule version.
**Exit criteria:**
- [ ] a saved trip round-trips (save → load equal) — `test_trip_roundtrip`
- [ ] only the last 3 schedule versions are kept; revert restores one — `test_version_cap_and_revert`
- [ ] `place_cache` evicts past TTL and re-fetches on access — `test_cache_ttl`
- [ ] durable tables contain no coordinates (ADR-001) — `test_no_coords_in_durable_tables`
- [ ] a trip can be created and reopened through the browser — `test_web_trip_create_reopen`
**Validation:** `python run_cli.py save ...; trip open <id>; trip revert <id> <v>`; in the browser, create a trip, reopen it, revert; inspect `*.db` to confirm no coords in durable tables.
**Architecture note:** the htmx shell (base templates, error→page mapping) is built once here; later milestones add one page each.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | `services/repository/schema.sql` — durable tables + place_cache (TTL) | standard | sonnet | schema per ADR-004 | M0 |
| 2 | repository: connect, init/migrate, CRUD trips/interests/ratings/anchors | standard | sonnet | repo pattern | 1 |
| 3 | schedule_versions: save, list, keep-last-3, revert | standard | sonnet | versioning | 2 |
| 4 | place_cache read/write + TTL eviction (no coords durable) | standard | sonnet | ADR-001 compliance | 1 |
| 5 | save/open/revert use-cases + CLI + `POST/GET /trips`, `/versions`, `/revert` | standard | sonnet | wire | 2,3 |
| 6 | web UI shell: base templates, htmx setup, error→page mapping | standard | sonnet | one-time UI foundation | M0 |
| 7 | trip create / list / open pages (htmx) | standard | sonnet | first real UI | 5,6 |
| 8 | persistence tests (round-trip, version cap+revert, cache TTL, no-coords) | standard | sonnet | correctness | 2,3,4 |
| 9 | web tests (create / reopen flow) | standard | sonnet | UI contract | 7 |

---

## Milestone 5 — Real place data + suggestions view
**Demo:** `plan --city Lisbon --interest "miradouros"` fetches real places (Google → OSM fallback), caches them, and **shows them in the browser** to rate — all within the free-tier guard.
**Exit criteria:**
- [ ] real candidates returned with structured coords + hours — `integration: test_google_search` (opt-in)
- [ ] Google failure falls back to OSM and marks `outcome: degraded` — `test_places_fallback`
- [ ] fetched data is written to `place_cache` and reused — `test_cache_write_reuse`
- [ ] the quota guard refuses calls past the ceiling (no billing) — `test_quota_guard`
- [ ] suggestions render in the browser with degraded / hours-unverified badges — `test_web_suggestions`
**Validation:** set keys in `.env`; `python run_cli.py plan --city Lisbon --interest "miradouros"`; open the trip in the browser; re-run and confirm cache hits in `logs/app.jsonl`.
**Degradation:** Google down/quota → OSM; all sources down → clear logged error + partials.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | config/secrets (pydantic-settings, caps) + `.env.example` | mechanical | haiku | config | M0 |
| 2 | `services/places/google.py` — text search + details | complex | opus | external API, security surface | 1 |
| 3 | `services/places/osm.py` — Overpass fallback | standard | sonnet | second provider | 1 |
| 4 | compose google→osm fallback + write to place_cache | standard | sonnet | fallback + cache | 2,3,M4 |
| 5 | QuotaGuard wrapper + tenacity retries | complex | opus | resilience + cost guard | 2 |
| 6 | `suggestions` use-case (literal query) + CLI `plan` + `POST /suggestions` | standard | sonnet | wire | 4 |
| 7 | suggestions view page (htmx) with degraded / unverified badges | standard | sonnet | UI for this feature | 6,M4 |
| 8 | observability spans/events on every external call | standard | sonnet | per ADR-006 | 2,3 |
| 9 | integration tests (opt-in) + degradation/fallback tests | complex | opus | failure injection | 4,5 |
| 10 | web test (suggestions view) | standard | sonnet | UI contract | 7 |

*Note: at the 10-task cap — splits if it grows at build time.*

---

## Milestone 6 — LLM curation + rating UI
**Demo:** `--interest "instagram cafés that serve more than coffee"` → Gemini turns it into searches, filters real candidates for fit (each with a `reasoning`), and you **rate them in the browser**.
**Exit criteria:**
- [ ] a free-text interest yields fit-filtered candidates, each with a `reasoning` — `test_fit_filter` (fixtures)
- [ ] curation chunks by interest and stays within the call budget — `test_call_budget`
- [ ] the interest library persists and per-trip activation works — `test_interest_library`
- [ ] LLM decisions + reasoning are logged at DEBUG (no secrets) — `test_llm_logging`
- [ ] the browser rating UI shows the reasoning and captures 1–5 + duration — `test_web_rating`
**Validation:** `python run_cli.py plan --city Lisbon --interest "<nuanced>"`; rate in the browser; inspect `logs/app.jsonl` for `call_kind`, `reasoning`, token counts.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | `services/llm.py` — Gemini client, structured-output discipline, config | complex | opus | external LLM, security | M5 |
| 2 | interest → search-query generation (batched) | standard | sonnet | prompt + parse | 1 |
| 3 | candidate fit-filter (chunked) + `reasoning` field | complex | opus | LLM judgment + chunking | 1,M5 |
| 4 | `gather_suggestions` use-case wired to LLM | standard | sonnet | orchestrate | 2,3 |
| 5 | interest library (persist, reuse, activation) + endpoints | standard | sonnet | CRUD | M4 |
| 6 | rating UI page: show reasoning, capture 1–5 + duration (htmx) | standard | sonnet | UI for this feature | 4,M4 |
| 7 | LLM span/events + DEBUG logging of output + reasoning | standard | sonnet | ADR-006 | 1 |
| 8 | tests (fit-filter, budget, library, logging, web rating) | complex | opus | correctness | 3,5,6 |

---

## Milestone 7 — Natural-language refinement (+ refine UI)
**Demo:** `refine <trip> "make day 2 more relaxed and end near the river"` (CLI or **browser**) → a new schedule version that honors the change and still respects anchors and hours.
**Exit criteria:**
- [ ] feedback becomes a structured sketch (swaps/params/soft-prefs), never clock times — `test_refine_sketch`
- [ ] the deterministic engine re-solves from the sketch; anchors stay honored — `test_refine_preserves_anchors`
- [ ] each refinement creates a new version (last-3 retained) — `test_refine_versions`
- [ ] an infeasible refinement returns a pushback, not a broken plan — `test_refine_infeasible`
- [ ] refining through the browser renders the result (or pushback) — `test_web_refine`
**Validation:** `python run_cli.py refine <id> "make day 2 more relaxed"`; refine the same trip in the browser.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | refine prompt: feedback + current plan + candidates → sketch (no schedule) | complex | opus | LLM→structured edits | M6 |
| 2 | `refine` use-case: apply sketch → re-solve (reuse M3 loop) → new version | standard | sonnet | reuse engine | 1,M3 |
| 3 | CLI `refine` + `POST /refine` (+ 409 on infeasible) | standard | sonnet | wire | 2 |
| 4 | refine box + pushback rendering (htmx) | standard | sonnet | UI for this feature | 3,M4 |
| 5 | reasoning + sketch logged at DEBUG | standard | sonnet | ADR-006 | 1 |
| 6 | tests (sketch shape, anchors preserved, versioning, infeasible, web refine) | complex | opus | correctness | 1,2,4 |

---

## Milestone 8 — Map
**Demo:** see candidate places and the routed schedule on a map, toggle days on/off, and export a static map image.
**Exit criteria:**
- [ ] options render as map markers — `test_map_options`
- [ ] the schedule renders day routes with a per-day toggle — `test_map_schedule`
- [ ] static map export produces a PNG — `test_static_export`
- [ ] map provider is pluggable (OSM default; Google swap path) — `test_map_provider_seam`
**Validation:** open the trip in the browser; toggle days; `python run_cli.py export <id> --format map`.

| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | map provider seam + Leaflet/OSM tiles default | standard | sonnet | pluggable per PRD | M7 |
| 2 | options on a map (markers) | standard | sonnet | rank view | 1 |
| 3 | schedule on a map (day routes + toggle) | standard | sonnet | presentation | 1 |
| 4 | static map export (PNG) via `maprender` | standard | sonnet | export | 1 |
| 5 | map tests (options, schedule, export, provider seam) | standard | sonnet | coverage | 2,3,4 |

---

## Notes

- Any milestone that reconciles to >10 tasks at `/build-milestone` time **splits** (new issue inserted, no sub-numbering) per the milestones skill. M5 is at the cap and most likely to split.
- Issue numbers fill in after `gh issue create`; this table is the source of order, issues are the source of identity.
