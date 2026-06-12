# Guardrails — hard rules for implementation

Each rule names the failure it prevents. Layered enforcement: some are also hooks/permissions (you'll be blocked or flagged); all are binding even where enforcement is prose-only.

## Tests and criteria (the corner-cutting cluster)

1. **Never weaken, delete, or skip a test to make it pass.** If a test seems wrong, stop and escalate with your reasoning — the test is the spec, and "the spec is wrong" is a human decision. (Backstop: hook flags added skip-markers; Stop hook blocks on red tests.)
2. **Never change exit criteria mid-milestone.** Same escalation path.
3. **No assertion-free tests.** A test that runs code without asserting on outputs/effects is corner-cutting wearing a coverage costume.

## Suppressions

4. `# noqa`, `# type: ignore`, `pytest.mark.skip`, broad `except Exception` — each requires an adjacent comment with a concrete justification. The pattern these prevent: suppressing the checker instead of fixing the finding. (Backstop: tripwire hook.)

## Scope and dependencies

5. **Declare your file list before coding; flag deviations.** Prevents the drive-by refactor that turns a 50-line diff into a 500-line review.
6. **No new dependencies without surfacing:** name, why, what existing dep/stdlib was considered. Prevents dependency sprawl from "import the first thing that works".
7. **Don't refactor adjacent code "while you're there"** — note it; `/audit` or a spun-off task owns it.

## Safety (also enforced by permission deny-rules)

8. No `git push --force`, `git reset --hard`, `rm -rf`, mass `git checkout --` discards.
9. Never commit secrets; .env files are read-only to you and never committed. (Backstop: gitleaks pre-commit.)
10. No destructive operations against anything shared (real APIs in write mode, user data files) without explicit user confirmation in this session.

## Honesty

11. **Report state faithfully:** failing tests are reported as failing, with output. Skipped steps are reported as skipped. "Done" means verified-done, not probably-done.
12. **3-attempt cap:** same error after 3 genuinely different fixes → stop, write what you tried + current hypothesis, escalate. Thrashing burns budget and usually means a wrong assumption upstream.
