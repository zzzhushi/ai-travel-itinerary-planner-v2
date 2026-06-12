# Parallel execution (--parallel)

## When it pays (decide honestly before using)

Parallelism pays on **wave-shaped** milestones: several tasks with no mutual dependencies AND mostly disjoint file sets (independent endpoints, separate pages, parallel adapters). It loses on **chain-shaped** milestones (model → store → handler → UI) and on tasks that touch the same files — there it converts waiting time into merge-conflict time plus duplicated context cost (~1.5–3× tokens). If fewer than 2 tasks share a wave, run sequential and say so.

## Wave construction

1. Topologically sort tasks by `depends_on`.
2. Wave = all tasks whose dependencies are complete. Within a wave, check **file-set overlap**: two tasks declaring the same file never share a wave — serialize them (cheaper than resolving the conflict they'd create).

## Worker briefs (the duplicated-context mitigation)

You have already read the PRD, issue, and code; workers must NOT repeat that discovery. Each brief contains conclusions, not pointers:

- Task description + the exit criterion it serves (excerpt, not the whole issue)
- Exact file list (may-modify / may-create / must-not-touch)
- Signatures + docstrings of interfaces the task consumes (not bodies)
- The 5–10 convention lines that matter for this task
- The implement-task loop and hard rules, inlined (workers can't see skills)
- Explicit: "Work only in your worktree. Do not re-explore the codebase broadly. Do not touch files outside your list. Commit on your branch when green. Your final message: files changed, test results, anything you flagged."

## Dispatch and monitoring

- One Agent call per task, all in one message, `isolation: "worktree"`, `model` from task metadata.
- Workers cannot ask you questions mid-flight: a worker that reports a blocker (ambiguity, missing dependency, guardrail conflict) gets its task re-specified and re-run, not patched by you reaching into its worktree.
- A worker that returns failing tests or scope violations: re-run once with the failure appended to the brief; second failure → take the task yourself sequentially.

## After each wave

Merge per merge-protocol.md (one branch at a time, full suite between merges) BEFORE constructing the next wave — later waves must build on merged reality, not on main-as-it-was.
