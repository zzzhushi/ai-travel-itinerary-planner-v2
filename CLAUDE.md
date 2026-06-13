# AI Travel Itinerary Planner v2

A travel itinerary planner built deliberately with a structured, skill-driven AI workflow. The skills in `.claude/skills/` ARE part of the product of this repo — they get dogfooded here and promoted to `~/.claude/skills` once proven.

## Workflow (the pipeline)

Lifecycle stages, each a skill: `/prd` → `/design` → `/milestones` → `/build-milestone <issue>` → `/ship`. Support skills: `/implement-task` (one-off tasks), `/debug`, `/audit` (periodic health), `/retro` (after each milestone, improves the skills themselves).

Human approval gates: PRD sign-off, mockup choice, roadmap approval, PR merge. Everything between gates runs autonomously.

## Artifacts (state lives in files and issues, never in conversation memory)

- `docs/prd.md` (project PRD), `docs/prds/<feature>.md` (feature PRDs)
- `docs/design/` — approved mockups + `design-system.md`
- `docs/roadmap.md` — milestones; one GitHub issue per milestone with exit criteria + task checklist
- `docs/engineering-standards.md` — the quality bar; read it before writing code
- `docs/decisions/` — ADRs, one file per contested decision (`README.md` is the index)

## Conventions

- **Verify command** (skills reference this line; update it here when tooling changes):
  `uv run ruff check && uv run mypy && uv run pytest -q`
- Branch per milestone: `milestone-<n>-<slug>`. Squash-merge via PR, `Closes #<issue>`. Commits on main are hook-blocked.
- Commit messages: 1–3 sentences, what + the non-obvious why. No play-by-play.
- Exit-criteria tests are written and committed BEFORE feature code in every milestone. Never weaken a test to make it pass — escalate instead.
- `.status_notes/` is the user's private notes directory — do not read or modify it.
