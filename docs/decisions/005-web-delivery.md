# ADR-005: Web delivery — FastAPI + Jinja2/htmx + Leaflet

Status: accepted (applies at the web-phase milestones) · Date: 2026-06-12

## Context

The PRD's web phase needs a local browser UI: trip creation forms, the rate-suggestions flow, a deterministically-rendered day view, and an **interactive map** (markers + day routes), all over the same `application/` use-cases the CLI uses. Constraints: free-tier ethos (free map tiles), single local user, and the operator is learning production Python.

## Options considered

1. **FastAPI + server-rendered (Jinja2 + htmx) + Leaflet on free OSM tiles.**
   - Pros: stays Python-centric — no separate JS build/toolchain; lean for a local single-user app; htmx covers the interactivity (partial updates) without an SPA; Leaflet + OSM tiles = free, keyed-by-nobody map; least context-switching from the backend.
   - Cons: less of the marketable "JS framework" skillset; rich client-side interactions are limited.
2. **FastAPI backend + React SPA.**
   - Pros: a real, industry-standard frontend skill; richest client interactivity.
   - Cons: build tooling, state management, a second language/ecosystem to maintain; heavy for a local hobby app; more surface for little v1 gain.
3. **Streamlit.**
   - Pros: fastest to a clickable Python-only UI.
   - Cons: limited layout/control, awkward for a custom map + bespoke flows; not a transferable production pattern.

## Decision

**FastAPI + Jinja2 + htmx + Leaflet (free OSM tiles).** The map provider stays pluggable (PRD): OSM tiles default, Google Maps JS a later swap for testing. Edits never happen client-side — user feedback goes through the deterministic re-solve — so the UI needs presentation + light interactivity, not a heavy client app.

## Consequences

- Fast path to a working web UI; the whole stack stays in Python + a little HTML/JS, matching the learning goal and the free-tier constraint.
- Trade-off accepted: less React/SPA experience; rich client-side state is intentionally out of scope (deterministic re-solve owns changes).
- This ADR is **ratified now but bites at web-phase slicing** — the engine/data milestones are unaffected by it.
- **Delivery is incremental, not horizontal:** each milestone exposes its use-case through a CLI command, a thin FastAPI endpoint ([api-contract.md](../api-contract.md)), and — from M4, where a persisted interactive app first exists — its own htmx UI page. A UI over the fixture-only engine (M1–M3) is premature, so those stay CLI/curl-driven. Only the map is a dedicated feature slice; the REST API and UI are validated continuously instead of in a big-bang web phase.
