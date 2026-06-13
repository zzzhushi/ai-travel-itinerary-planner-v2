# Engineering Standards

Decision rules for all code in this project. These are rules, not aspirations — each one is phrased so you can tell whether code complies. Skills reference this document; do not restate it inside skills.

## Testing

- Every public function/endpoint gets a happy-path test AND a failure-path test (bad input, dependency down).
- Every bug fix lands with a regression test that fails on the old code.
- Test behavior through the public interface, not implementation details. If a refactor that preserves behavior breaks the test, the test was wrong.
- Coverage is a CI ratchet: the build fails if coverage drops below the previous main-branch value. Never write tests "to raise coverage" — write them to pin behavior; coverage follows.
- A test with no meaningful assertion is worse than no test (it certifies nothing and costs maintenance). Each test asserts on output values or observable effects, not just "it didn't throw".

## Observability

Lives in its own package, `src/tripplanner/observability/`:
- `logging.py` — structlog config (JSON output) + sinks (stdout + rotating file `logs/app.jsonl`).
- `tracing.py` — OpenTelemetry setup; span exporters (console/file in dev, optional local Jaeger via OTLP).
- `context.py` — binds the per-run context (`correlation_id`, `trip_id`) so every log line inherits it; trace/span ids come from the active OTel span.
- `schema.py` — the canonical field names + typed helpers for emitting events, so fields don't drift.

**The standard fields** (`correlation_id` is on every line; `trace_id`/`span_id` appear on lines emitted within a span — a log outside any operation legitimately carries no trace; the goal is that a failed build is diagnosable from telemetry alone):

| Field | Meaning |
|---|---|
| `time` · `level` · `event` | ISO-8601 UTC · severity · event name |
| `correlation_id` | one per CLI run / HTTP request — the thread you follow end to end |
| `trace_id` · `span_id` | OpenTelemetry; correlate logs ↔ spans |
| `trip_id` | domain context when operating on a trip |
| `component` | `domain` · `places` · `llm` · `travel` · `repository` · `cli` · `web` |
| `operation` | e.g. `places.search` · `schedule.build` · `llm.fit_filter` |
| `duration_ms` · `outcome` | on completion of an operation: `ok` · `degraded` · `error` |
| `error.type` · `error.message` | on failure |
| external calls add | `provider` · `endpoint` · `attempt` · `http_status` · `cache` (hit/miss) · `quota_remaining` |
| LLM calls add | `model` · `call_kind` · `input_tokens` · `output_tokens` |

Rules:
- Logs serve **two readers: a human and a coding agent** (the `/debug` and `/build-milestone` loops read them to self-diagnose). Write events and fields so either can trace a failure without a debugger or the source open — this is the bar, not an extra.
- No bare `print()` outside CLI user-facing output.
- A span wraps each use-case and each external call (with `duration_ms` + `outcome`); logs reference the active `trace_id`.
- Log at decision points and boundaries, not every line.
- **Never** log secrets, API keys, or full prompts. `logs/` is gitignored.

## Errors and resilience

- Retries (with exponential backoff + jitter, via `tenacity`) only at external-call boundaries. Never retry around internal logic — fix the logic.
- Each feature's milestone defines its graceful-degradation behavior (e.g. "LLM unavailable → cached itinerary + banner"). If none is defined, fail loudly, don't improvise a fallback.
- Never swallow an exception silently. Catch only what you can handle; re-raise or log-with-context otherwise. `except Exception: pass` is banned.

## Python idioms (notes for the ex-C# reader)

- Define a `Protocol` only where you will mock it in tests or a second implementation is already planned (LLM client, storage, external APIs). Everywhere else, write plain functions and classes. No single-implementation ABCs, no getter/setter ceremony.
- `pydantic` models at boundaries (API request/response, LLM I/O, config); plain dataclasses or primitives internally.
- Type hints on everything; `mypy --strict` must pass. A `# type: ignore` requires an adjacent comment explaining why.
- Prefer module-level functions over classes when there's no state. A class with one method and no state is a function.

## Comments and docs

- Comment only non-obvious decisions and constraints (the "why"); never narrate what the code does.
- README quickstart must actually work — it is re-verified during `/audit`.
- Each decision where a real alternative was seriously considered gets an ADR in `docs/decisions/NNN-slug.md` (Context / Options / Decision / Consequences — template in the milestones skill). Routine choices don't; the gate is "was there a genuine fork in the road".

## Tooling

- `uv` for environments and dependencies. `ruff` for lint + format. `mypy --strict`. `pytest`. `pre-commit` with gitleaks.
- New dependencies must be surfaced before adding: name, why, and what stdlib/existing dep was considered instead.
