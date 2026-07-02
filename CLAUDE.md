# AI Travel Itinerary Planner v2

A travel itinerary planner built deliberately with a structured, skill-driven AI workflow. The skills in `.claude/skills/` ARE part of the product of this repo — they get dogfooded here and promoted to `~/.claude/skills` once proven.

## Workflow (the pipeline)

Lifecycle stages, each a skill: `/prd` → `/design` → `/milestones` → `/build-milestone <issue>` → `/ship`. Support skills: `/implement-task` (one-off tasks), `/debug`, `/audit` (periodic health), `/retro` (after each milestone, improves the skills themselves).

Human approval gates: PRD sign-off, mockup choice, roadmap approval, PR merge. Everything between gates runs autonomously.

## Artifacts (state lives in files and issues, never in conversation memory)

- `docs/prd.md` (project PRD), `docs/prds/<feature>.md` (feature PRDs)
- `docs/design/` — approved mockups + `design-system.md`
- `docs/roadmap.md` — milestones; one GitHub issue per milestone with exit criteria + task checklist
- `docs/api-contract.md` — the operation/endpoint contract (use-cases = API); CLI and web both implement it
- `docs/engineering-standards.md` — the quality bar (incl. the observability field schema); read it before writing code
- `docs/design-doc.md` — the living system design doc (Gate 1 artifact); deviations from it pause for the user
- `docs/debt.md` — tech-debt ledger; 3rd sighting promotes an item to a milestone task
- `docs/decisions/` — ADRs, one file per contested decision (`README.md` is the index)

## Conventions

- **Verify command** (skills reference this line; update it here when tooling changes):
  `uv run ruff check && uv run mypy && uv run pytest -q`
- Branch per milestone: `milestone-<n>-<slug>`. Squash-merge via PR, `Closes #<issue>`. Commits on main are hook-blocked.
- Commit messages: **2 sentences max** — what + the non-obvious why. All other context goes in the PR description or comments, never the commit body.
- Exit-criteria tests are written and committed BEFORE feature code in every milestone. Never weaken a test to make it pass — escalate instead.
- `.status_notes/` is the user's private notes directory — do not read or modify it.
