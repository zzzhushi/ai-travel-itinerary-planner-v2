# Logging & Event Catalog

How diagnostics are emitted, and the catalog of every event code. Goal: from a **run
directory alone**, a coding agent can localize a failure, explain any decision, and
deterministically replay the run (see PRD §13.2).

Status: **stub** — event codes below are the planned contract; fields firm up during M0/M2.

---

## Telemetry standard: OpenTelemetry

Instrumentation is built on **OpenTelemetry (traces as the primary signal)** — the
vendor-neutral industry standard. The pipeline maps onto OTel primitives:

| Our model | OTel primitive |
|---|---|
| run | root **span** (its `trace_id` is the `run_id`) |
| stage (curate/resolve/cluster/schedule) | child **span** |
| decision (`sched.drop`, `resolve.hours`) | **span event** on the stage span |
| provenance `data` (failed_constraint, source, confidence) | **span attributes** |

- **FastAPI auto-instrumentation** (`opentelemetry-instrumentation-fastapi`) traces the API
  layer with near-zero code.
- **Custom JSONL exporter** (a span processor) maps spans/events/attributes → the documented
  event schema below, preserving the agent-debuggable flat file. The `event` codes in the
  catalog become span names (stages) and span-event names (decisions).
- **Optional OTLP exporter** behind a flag → push to a local **Jaeger / Grafana Tempo**
  container (still no hosted backend) to exercise the full industry workflow.
- **Replay is separate:** OTel is *observation only*. The replay source remains
  `manifest.json` + the SQLite response cache (capability #4) — telemetry never replaces it.

> Note: OTel's *traces* are the mature core we rely on; its *logs* signal is newer — we use
> the JSONL exporter for the human/agent-readable log rather than the OTel logs SDK.

---

## Format

- **JSONL** — one JSON object per line, append-only, one file per run, produced by the custom
  OTel span exporter: `runs/<trip_id>/<run_id>/trace.jsonl`.
- Companion **manifest**: `runs/<trip_id>/<run_id>/manifest.json` (replay inputs).
- Levels: `DEBUG | INFO | WARN | ERROR`.

### Common fields (every line)
| Field | Type | Notes |
|---|---|---|
| `ts` | ISO-8601 | event time |
| `level` | string | DEBUG/INFO/WARN/ERROR |
| `run_id` | string | unique per engine run |
| `trip_id` | string | stable per trip |
| `version` | int | itinerary version this run produced/edited |
| `stage` | string | `curate \| resolve \| cluster \| schedule \| explain \| feedback` |
| `component` | string | emitting module (e.g. `scheduler.order`) |
| `event` | string | stable code from the catalog below |
| `msg` | string | short human summary |
| `data` | object | event-specific payload (see catalog) |

### Manifest (`manifest.json`) — replay inputs
`config snapshot`, `model_id`, `prompt_version` + `prompt_hash`, `rng_seed(s)`,
`code_version` (git sha), `trip_yaml_hash`, `cache_db_ref`. Together with the SQLite
response cache these make a run replayable offline.

---

## Event catalog

### Lifecycle
| event | level | `data` highlights |
|---|---|---|
| `run.start` | INFO | manifest summary, input hashes |
| `run.finish` | INFO | duration, version, llm_call_count, dropped_count |
| `run.error` | ERROR | failing stage, exception, failing input |

### Stage boundaries (capability #1 — localize)
| event | level | `data` highlights |
|---|---|---|
| `stage.in` | DEBUG | stage, input snapshot or hash |
| `stage.out` | DEBUG | stage, output snapshot or hash, item counts |

### External calls (capability #3 — trace)
| event | level | `data` highlights |
|---|---|---|
| `ext.call` | INFO | service, endpoint, params_hash, latency_ms, status, cache_hit |
| `ext.retry` | WARN | service, attempt, backoff_ms, reason |
| `ext.quota` | WARN | service, quota_state |
| `ext.fallback` | WARN | from→to (e.g. `gemini→cache`, `ors→haversine`, `llm→overpass`) |

### Curator / LLM
| event | level | `data` highlights |
|---|---|---|
| `llm.request` | DEBUG | role (curator/editor/narrator), prompt_hash, schema |
| `llm.response` | DEBUG | response_hash, n_items |
| `llm.schema_fail` | WARN | validation error, self_heal_attempt |

### Resolver (capability #2 — provenance)
| event | level | `data` highlights |
|---|---|---|
| `resolve.geocode` | DEBUG | place, coords, source, confidence |
| `resolve.hours` | DEBUG | place, source, confidence, day_of_week handling |
| `resolve.duration` | DEBUG | place, minutes, source |
| `resolve.drop` | WARN | place, reason (e.g. `no_geocode`), backfilled |

### Scheduler (capability #2 — provenance)
| event | level | `data` highlights |
|---|---|---|
| `sched.cluster` | DEBUG | day, cluster_count, members |
| `sched.order` | DEBUG | day, ordered_stops, total_travel_min |
| `sched.penalty` | DEBUG | term, value (inter_cluster / overpack) |
| `sched.move` | INFO | place, from_day→to_day, reason |
| `sched.drop` | INFO | place, must_see, failed_constraint, blocking_anchor, Δobjective |
| `sched.anchor_fixed` | DEBUG | anchor, day, window |

### Feedback / refinement
| event | level | `data` highlights |
|---|---|---|
| `feedback.lever` | INFO | changed weights, deterministic re-solve (no LLM) |
| `feedback.content` | INFO | free-text, triggers Editor call |
| `feedback.lock` | INFO | place/day locked → temporary anchor |
| `version.snapshot` | INFO | version, path |

---

## Replay acceptance test (PRD §13.2)

> Given only a run directory (`manifest.json` + `trace.jsonl` + cache), `replay` reproduces
> the identical itinerary and decision log offline.

This doubles as the engine-determinism guarantee for the test suite.
