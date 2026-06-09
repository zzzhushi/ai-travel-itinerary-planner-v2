# OpenTelemetry instrumentation with a custom Postgres exporter

The app is instrumented with the real OpenTelemetry SDK (tracers, spans, attributes,
and FastAPI/HTTP-client auto-instrumentation later). Telemetry is persisted by a
**custom SpanProcessor/exporter that writes to Postgres** (`log_event`, `llm_call`,
spans) with JSONB payloads and our domain fields (`trip_id`, token counts,
`geo_source`, `cache_hit`).

The OTel **`trace_id` is our request_id.** Each top-level operation opens a trace; the
FastAPI layer returns its `trace_id` in an `X-Request-ID` response header so any
request can be traced directly to its Postgres log rows.

## Considered Options

- *Jaeger/Tempo + Grafana* — most idiomatic, but telemetry would be queried in Grafana,
  not SQL; the explicit requirement is SQL-queryable logs in Postgres.
- *OTel Collector → Postgres* — production-grade but adds a Collector process to run
  locally.
- *Hand-rolled logger* — rejected: forgoes the industry-standard OTel skill and
  auto-instrumentation.

## Consequences

- We own a small amount of exporter code, but get real OTel semantics *and* SQL-queryable
  diagnostics in one store.
- `trace_id`/`span_id` are general observability terms and deliberately kept out of
  CONTEXT.md (glossary is domain language only).
