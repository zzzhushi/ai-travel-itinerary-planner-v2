# Engineering Standards

Decision rules for all code in this project. These are rules, not aspirations — each one is phrased so you can tell whether code complies. Skills reference this document; do not restate it inside skills.

## Testing

- Every public function/endpoint gets a happy-path test AND a failure-path test (bad input, dependency down).
- Every bug fix lands with a regression test that fails on the old code.
- Test behavior through the public interface, not implementation details. If a refactor that preserves behavior breaks the test, the test was wrong.
- Coverage is a CI ratchet: the build fails if coverage drops below the previous main-branch value. Never write tests "to raise coverage" — write them to pin behavior; coverage follows.
- A test with no meaningful assertion is worse than no test (it certifies nothing and costs maintenance). Each test asserts on output values or observable effects, not just "it didn't throw".

## Observability

- Structured logging via `structlog`, JSON output. No bare `print()` outside CLI user output.
- Every API boundary attaches a `request_id` (generated) and propagates a `correlation_id` (from header if present, else = request_id). Both appear in every log line for that request and in error responses.
- Log at decision points and external-call boundaries — with duration and outcome — not every line. The bar: an unexpected failure must be diagnosable from logs alone, without a debugger.
- External calls (LLM, HTTP, DB) log: target, duration, outcome, and the ids above. Never log secrets, tokens, or full prompts at INFO.

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
- Each architectural decision that wasn't obvious gets a short note in `docs/decisions.md` (one paragraph: context, decision, why).

## Tooling

- `uv` for environments and dependencies. `ruff` for lint + format. `mypy --strict`. `pytest`. `pre-commit` with gitleaks.
- New dependencies must be surfaced before adding: name, why, and what stdlib/existing dep was considered instead.
