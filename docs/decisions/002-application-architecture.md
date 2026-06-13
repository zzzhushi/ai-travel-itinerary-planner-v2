# ADR-002: Layered architecture with a pure domain core

Status: accepted · Date: 2026-06-12

## Context

The planner has three structural forces: (1) the PRD requires the scheduling engine to be unit-testable with **no LLM and no network**; (2) several **second implementations are already planned** — OSM fallback for places, a local LLM, Google Routes for travel (v2), OR-Tools for scheduling; (3) **two delivery surfaces** (CLI now, web later) must share one business core. How should the codebase be structured?

## Options considered

1. **Pragmatic hexagonal (ports & adapters).** Define `Protocol` interfaces at the I/O edges (PlaceData, LLM, Travel, Repository); application depends on the ports; adapters implement them; one composition root wires concrete adapters.
   - Pros: swapping any external service = add an adapter class, wired once, core untouched; use-cases tested by injecting fakes; the planned swaps and dual delivery are first-class.
   - Cons: ~4 interface definitions + a composition root of upfront structure; more indirection than a small app strictly needs.
2. **Layered / transaction-script.** Use-cases in `application/` call service modules in `services/` directly; a pure `domain/` holds the engine; no port interfaces.
   - Pros: less upfront structure, fewer files, faster to first running code; still cleanly separates pure rules (`domain/`) from I/O (`services/`).
   - Cons: swapping a backend means editing the service module (or a contained refactor toward injection later); use-case tests rely on monkeypatch/fakes rather than injection; the I/O coupling the PRD's planned swaps will pressure is in the application layer.

## Decision

**Layered**, with a hard rule that `domain/` (models, scheduler, feasibility, durations) imports nothing from `services/` and performs no I/O — so the engine stays offline-testable regardless of architecture style. `application/` use-cases orchestrate `services/` (external I/O) and `domain/` (pure rules). `cli.py` / `web/` are thin delivery shells.

Chosen over hexagonal for less upfront ceremony, accepting that multiplying second-implementations may later motivate introducing injection seams at specific integrations (see the file→subpackage+factory growth rule below).

## Consequences

- **The one inviolable rule:** no `from tripplanner.services …` inside `domain/`. If that import appears, the offline-testability guarantee (and `tests/unit/domain` needing no mocks) has broken. Worth a lint/CI check.
- **Adding a backend** = edit the relevant `services/` module, or **promote a single-impl module to a subpackage with a factory** when a second implementation lands (`services/llm.py` → `services/llm/{gemini,local}.py` + factory). The shared shape for such an integration is the one place a thin `Protocol` is justified.
- **Use-case tests** use monkeypatch or pass fakes; integration tests hit real APIs and are kept out of fast CI.
- **Revisit** toward injection if the number of swappable integrations grows enough that monkeypatch-heavy tests become a drag — a superseding ADR would record that shift.
