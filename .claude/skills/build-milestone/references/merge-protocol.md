# Merge protocol (after a parallel wave)

Rule zero: **one branch at a time, full test suite after each merge.** Batch-merging then testing once tells you something broke but not which merge broke it.

1. Order branches: fewest-files-changed first (smallest conflict surface lands cheapest).
2. For each worker branch, on the milestone branch:
   ```bash
   git merge --no-ff <worker-branch>
   uv run ruff check && uv run mypy && uv run pytest -q
   ```
3. **Textual conflict:** resolve only if trivial (imports, adjacent additions). Anything where both sides changed the same logic → abort the merge (`git merge --abort`) and re-run that task sequentially on top of the current milestone branch. Re-running a 10-minute task is cheaper than a subtle bad resolution.
4. **Semantic conflict** (merge clean, tests now fail): the new code and merged reality disagree — e.g. both workers invented a helper, or an interface drifted. Diagnose; if the fix is local and obvious, fix it with a commit explaining the collision; otherwise re-run the losing task against current reality.
5. After all merges: run the milestone's exit-criteria tests + duplication scan — parallel workers independently inventing the same utility is the most common semantic drift; consolidate before verification.
6. Clean up: delete merged worker branches; `git worktree prune` (the Agent tool auto-removes unchanged worktrees; changed ones persist until their branch is merged).

Never resolve a conflict by deleting a test, and never use `-X ours/theirs` blanket strategies — both are silent spec edits.
