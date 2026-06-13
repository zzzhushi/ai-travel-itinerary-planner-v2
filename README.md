# AI Travel Itinerary Planner

Plan a realistic day-by-day itinerary for a few days in a city: rate real places
by interest, and a deterministic scheduler routes them so each day stays compact
and respects opening hours. Built deliberately with a structured, skill-driven AI
workflow (see `docs/` and `.claude/skills/`).

> **Status: early scaffolding (Milestone 0).** The routing engine, real place
> data, LLM curation, and web UI arrive in later milestones — see
> [docs/roadmap.md](docs/roadmap.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environments and dependencies

## Setup

```bash
uv sync                      # create the venv and install everything
uv run pre-commit install    # optional: enable lint + secret-scan git hooks
```

## Run it

```bash
# CLI (three equivalent entrypoints)
uv run python run_cli.py --version
uv run python -m tripplanner --version
uv run tripplanner --version

# Web API on http://localhost:8000
uv run uvicorn tripplanner.web.app:app
curl localhost:8000/health   # -> {"status":"ok","version":"0.1.0"}
```

## Develop

Run the verify command before every commit:

```bash
uv run ruff check && uv run mypy && uv run pytest -q
```

Coverage is a **ratchet, not a target**: CI fails if it drops below
`.coverage-baseline`, and the floor only rises when you commit an improved value.
The full quality bar — including the observability field schema — lives in
[docs/engineering-standards.md](docs/engineering-standards.md).

## Project layout

```
src/tripplanner/
  domain/         pure scheduling logic, no I/O (ADR-002)
  services/       external integrations (places, llm, travel, repository)
  application/    use-cases orchestrating domain + services
  observability/  structured logging + OpenTelemetry tracing (ADR-006)
  web/            FastAPI app
  cli.py          command-line entry point
docs/             PRD, roadmap, API contract, ADRs, engineering standards
```

## Docs

- [docs/prd.md](docs/prd.md) — what we're building and why
- [docs/roadmap.md](docs/roadmap.md) — milestones and status
- [docs/api-contract.md](docs/api-contract.md) — the operation/endpoint contract (CLI and web both implement it)
- [docs/decisions/](docs/decisions/) — architecture decision records
- [docs/engineering-standards.md](docs/engineering-standards.md) — the quality bar
