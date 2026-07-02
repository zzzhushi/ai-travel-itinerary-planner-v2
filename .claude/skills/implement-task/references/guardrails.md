# Guardrails — hard rules for implementation

Each rule names the failure it prevents. These are tripwires, not a checklist to narrate: most never fire on a given task; when one is relevant, it's binding. Layered enforcement: some are also hooks/permissions (you'll be blocked or flagged); all are binding even where enforcement is prose-only.

## Tests and criteria (the corner-cutting cluster)

1. **Never weaken, delete, or skip a test — or change an exit criterion — to make something pass.** If a test seems wrong, stop and escalate with your reasoning — the test is the spec, and "the spec is wrong" is a human decision. (Backstops: hook flags added skip-markers; Stop hook blocks on red tests.)
2. **No assertion-free tests.** A test that runs code without asserting on outputs/effects is corner-cutting wearing a coverage costume.

## Suppressions

3. `# noqa`, `# type: ignore`, `pytest.mark.skip`, broad `except Exception` — each requires an adjacent comment with a concrete justification. The pattern this prevents: suppressing the checker instead of fixing the finding. (Backstop: tripwire hook.)

## Scope and dependencies

4. **Declare your file list before coding; flag deviations.** Prevents the drive-by refactor that turns a 50-line diff into a 500-line review.
5. **No new dependencies without surfacing:** name, why, what existing dep/stdlib was considered. Also a sync-pause trigger (implement-task step 1). Prevents dependency sprawl from "import the first thing that works".
6. **Clean the code you're modifying; leave adjacent code alone.** Within your declared file list, small refactors that make the change cleaner are *required*, not forbidden — done first, as their own `refactor:` commit. Outside that list, or larger than a prep refactor: `docs/debt.md` or propose it. Prevents both failure modes: the drive-by refactor AND the "not my job" duplication pile-up.
7. **Walk the decision ladder before any new code:** does it need to exist → does the codebase have it (search first) → stdlib → platform natives → existing deps → only then minimal new code. A helper needs ≥2 real call sites; no speculative params, config, or interfaces-with-one-implementation. Where a deliberate simplification is one a reviewer would plausibly flag, mark it with a one-line ceiling comment (`# linear scan; fine ≤1k places, spatial index if catalogs grow`) — *deliberately simple* must be distinguishable from *didn't think about it*, or a future reader re-litigates or "fixes" it. Prevents gold-plating and write-time duplication; don't comment everything — noise buries signal.
8. **Contract sync:** any change to externally observable behavior (HTTP status/shape, CLI flags/output, wire formats) updates `docs/api-contract.md` in the same logical unit and is called out in the PR body. Contract *changes* are also a sync-pause trigger; additions just sync the doc. Prevents the contract doc silently drifting from the code.
9. **Debt goes to the ledger.** Deferred or disputed review findings land in `docs/debt.md` (one line: what, where, sighting count), never in PR-comment limbo. Third sighting promotes it to a real task. Prevents known debt evaporating.

## Safety (also enforced by permission deny-rules and hooks)

10. No destructive git (`push --force`, `reset --hard`, `rm -rf`, mass `checkout --` discards); never commit secrets (`.env` is read-only; gitleaks backstop); no destructive operations against anything shared (real APIs in write mode, user data files) without explicit user confirmation in this session.

## Honesty

11. **Report state faithfully:** failing tests are reported as failing, with output. Skipped steps are reported as skipped. "Done" means verified-done, not probably-done.
12. **3-attempt cap:** same error after 3 genuinely different fixes → stop, write what you tried + current hypothesis, escalate. Thrashing burns budget and usually means a wrong assumption upstream.
