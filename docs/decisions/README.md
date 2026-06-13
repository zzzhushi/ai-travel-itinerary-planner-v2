# Architecture Decision Records

One file per decision where a real alternative was seriously considered (the gate — routine choices live in the PRD decisions log instead). Template: `.claude/skills/milestones/references/adr-template.md`. Accepted ADRs are never rewritten — they get superseded.

## Index

| ADR | Decision | Status |
|---|---|---|
| [001](001-place-data-source.md) | Structured place-data API (Google Places New) as source of truth; LLM curates | accepted |
| [002](002-application-architecture.md) | Layered architecture with a pure domain core (over hexagonal) | accepted |
| [003](003-scheduler-heuristic.md) | Scheduler: custom heuristic first, OR-Tools as a contained swap | accepted |
| [004](004-persistence-sqlite-cache.md) | SQLite with a TTL place-cache separate from durable tables | accepted |
| [005](005-web-delivery.md) | Web delivery: FastAPI + Jinja2/htmx + Leaflet (over React SPA) | accepted |
