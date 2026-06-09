# UI-agnostic core, CLI first, FastAPI+React as the UI target

All domain logic (Gemini calls, geo resolution, ranking, scheduling, persistence)
lives in a `core` package that knows nothing about how it is presented. Interfaces
are thin adapters over the core.

- **Now:** a Typer/Click **CLI** is the first adapter — it doubles as the intermediate
  build and the primary diagnostic/test harness while the hard parts (scheduler, geo,
  Gemini) are proven.
- **Later:** a **FastAPI** API + **React** frontend wraps the same core, chosen so the
  author builds industry-standard, transferable skills.

The core never imports from an adapter; adapters depend only on the core's public API.

## Consequences

- Logic is tested directly against the core, independent of any UI.
- Adding the web UI is "wrap the core a second time," not a rewrite.
- The core's public functions must be designed as a stable, serialisable API surface
  from day one (clean inputs/outputs), since both CLI and a future HTTP layer call it.
