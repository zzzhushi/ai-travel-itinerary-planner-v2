# ADR-003: Scheduler — custom heuristic first, OR-Tools as a contained swap

Status: accepted · Date: 2026-06-12

## Context

Each day's route is a **Traveling Salesman Problem with Time Windows (TSPTW)**: order a handful-to-~dozen stops to minimize travel while respecting opening hours, per-place visit durations, the daily time budget, and **fixed anchors as hard (tight) time windows**. The engine must be deterministic, offline-testable, and honest about infeasibility. What solves the per-day routing?

## Options considered

1. **Custom heuristic** — geographic day-clustering, then per day an insertion heuristic (seed fixed anchors at their pinned times; greedily insert remaining stops, highest-rated first, into the cheapest window-feasible gap) + a window-respecting local-search (2-opt/or-opt) pass.
   - Pros: tiny dependency surface (pure Python); fully transparent and debuggable; trivially unit-testable; plenty for a dozen stops; the deterministic feasibility check (ADR scope) catches true infeasibility.
   - Cons: not provably optimal; tight multi-anchor days need careful window-feasibility logic; hand-rolled routing can harbor subtle bugs.
2. **Google OR-Tools routing solver** — model TSPTW with native time-window dimensions.
   - Pros: battle-tested, near-optimal even on tricky anchor cases; time windows are first-class.
   - Cons: heavy C++ dependency to install; steeper API; arguably overkill at this scale; more to learn before the engine runs end-to-end.

## Decision

**Heuristic first**, implemented behind a stable function signature (`schedule(places, constraints, travel) -> Itinerary`) so an OR-Tools implementation can replace it without touching callers if a real tight-anchor case ever exceeds the heuristic. The deterministic feasibility check remains the authority on "this can't fit."

## Consequences

- Minimal dependencies; the most-tested, most-critical code stays pure Python and easy to reason about.
- Suboptimality risk is bounded by the small problem size, exhaustive unit tests on routing/window cases, and the feasibility pushback for genuinely infeasible requests.
- The swap path is defined: same signature, new implementation module; revisit if users hit anchor-dense days the heuristic mis-routes.
