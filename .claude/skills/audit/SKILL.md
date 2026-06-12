---
name: audit
description: Periodic codebase health pass — security, structure quality, documentation freshness. Run every few milestones or before sharing the project ("audit the codebase", "health check", "is the code still clean").
---

# Audit: Periodic Health Pass

Three passes, each producing findings — not fixes. The user decides what becomes an issue; the audit that quietly "fixes" things is an unreviewed refactor.

## 1. Security

Run the built-in `/security-review`. Additionally check the project-specific surfaces it may not weight: secrets hygiene (`.env` handling, anything in git history), LLM-specific issues (prompt injection paths from user input into prompts, PII sent to external APIs vs. the PRD's privacy constraints), dependency freshness (`uv lock --check` / known CVEs).

## 2. Structure

Compare reality against `docs/engineering-standards.md`, looking for drift that accumulates across milestones (each was individually fine):

- Duplication — same logic grown independently in 2+ places (parallel execution makes this the top suspect)
- Dead code — unreferenced functions, never-true branches, orphaned files
- Boundary erosion — pydantic-at-boundaries violated, Protocols multiplying without second implementations or mocks, module dependency cycles
- Test health — assertion-free tests, suppression comments without justification, coverage-ratchet bypasses
- Use the built-in `/simplify` for reuse/simplification candidates; fold its output into findings

## 3. Documentation freshness

- **Execute** the README quickstart verbatim in a clean shell — it works or it's a finding
- `docs/decisions.md` entries still true? (superseded decisions get marked, not deleted)
- Roadmap status matches reality; engineering-standards still matches actual practice (if practice drifted for a good reason, the *doc* might be the finding)

## Output

One findings list, each item: severity (fix-now / next-milestone / someday), one-line evidence, proposed action. Present to the user; create GitHub issues only for what they accept (`gh issue create`, label `audit`). Note the audit date in `docs/roadmap.md` so the cadence is visible.
