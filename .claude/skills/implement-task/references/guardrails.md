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
6. **No new dependencies without surfacing:** name, why, what existing dep/stdlib was considered. Prevents dependency sprawl from "import the first thing that works". (Also a sync-pause trigger — see implement-task step 1.)
7. **Clean the code you're modifying; leave adjacent code alone.** Within your declared file list, small refactors that make the change cleaner are *required*, not forbidden — done first, as their own `refactor:` commit. Outside that list, or larger than a prep refactor: note it in `docs/debt.md` or propose it (sync trigger if it's load-bearing). Prevents both failure modes: the drive-by refactor AND the "not my job" duplication pile-up.
8. **Walk the decision ladder before any new helper/abstraction:** does it need to exist → does the codebase have it (search first) → stdlib → platform natives → existing deps → only then minimal new code. A helper needs ≥2 real call sites; no speculative params, config, or interfaces-with-one-implementation. Internal discipline — never surfaces to the user unless a sync trigger fires. Prevents gold-plating and the `_hhmm`-duplicated-in-two-files class of debt at write time.
9. **Ceiling comments on deliberate simplifications — scoped.** Where the limitation is real and a reviewer would plausibly flag it, one line naming the limit + upgrade trigger: `# linear scan; fine ≤1k places, spatial index if catalogs grow`. A future reader can't distinguish *deliberately simple* from *didn't think about it* — and either re-litigates or "fixes" it into complexity you rejected. Don't comment everything; noise buries signal.
10. **Contract sync:** any change to externally observable behavior (HTTP status/shape, CLI flags/output, wire formats) updates `docs/api-contract.md` in the same logical unit and is called out in the PR body. Prevents the contract doc silently drifting from the code. (Contract *changes* are also a sync-pause trigger; additions just sync the doc.)
11. **Debt goes to the ledger.** Deferred or disputed review findings land in `docs/debt.md` (one line: what, where, sighting count), never in PR-comment limbo. Third sighting promotes it to a real task. Prevents known debt evaporating.

## Safety (also enforced by permission deny-rules)

12. No `git push --force`, `git reset --hard`, `rm -rf`, mass `git checkout --` discards.
13. Never commit secrets; .env files are read-only to you and never committed. (Backstop: gitleaks pre-commit.)
14. No destructive operations against anything shared (real APIs in write mode, user data files) without explicit user confirmation in this session.

## Honesty

15. **Report state faithfully:** failing tests are reported as failing, with output. Skipped steps are reported as skipped. "Done" means verified-done, not probably-done.
16. **3-attempt cap:** same error after 3 genuinely different fixes → stop, write what you tried + current hypothesis, escalate. Thrashing burns budget and usually means a wrong assumption upstream.
