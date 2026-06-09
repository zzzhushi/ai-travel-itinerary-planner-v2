# SQLite for domain state, Postgres for logs

Domain/Trip state (Trip, Category, Interest, Option, rankings, Schedule) is stored in
**SQLite**, behind a repository interface. Logs/telemetry are stored in **Postgres**
(see ADR-0003). The two stores are independent; log rows carry `trip_id` and
`request_id`/`trace_id` to correlate back to domain state.

## Rationale

- SQLite fits a local, single-user, resumable tool: one file, zero setup, transactional,
  and an in-memory database makes the test suite near-instant.
- Postgres fits logs: JSONB payloads, indexing/querying over high-volume append-only
  events, concurrent writes, retention.

## Consequences

- The repository interface means "swap domain state to Postgres" is a one-adapter change
  when the FastAPI+React app goes multi-user (ADR-0002).
- Two datastores to run for the full experience, but only SQLite is needed to plan a trip
  via the CLI; Postgres is required only when telemetry is enabled.
