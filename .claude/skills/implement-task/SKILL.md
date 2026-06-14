---
name: implement-task
description: The single-task implementation discipline — test-first, guarded, committed. Invoked by /build-milestone per task, embedded in parallel-worker briefs, or used standalone for one-off tasks ("implement-task add a --currency flag", optionally --local for local-LLM routing of mechanical tasks).
---

# Implement Task

This skill is **self-contained by design**: parallel workers receive it cold, with no conversation history. Everything needed to do one task correctly is here or in the task brief.

## Inputs

A task brief containing: the task description, its complexity/model rating, the milestone exit criteria it serves, intended file paths, relevant interfaces/conventions, and `depends_on` state. Standalone use (a user types `/implement-task <description>`): construct the brief yourself — read `docs/engineering-standards.md` and the relevant code first; if the task is ambiguous, ask before coding.

## The loop

1. **Restate scope.** Write down (in the issue checklist or your response): the task in your own words + the exact file list you intend to touch. Work outside that list = stop and flag scope creep before proceeding.
2. **Failing test first.** If the task's behavior isn't already pinned by a committed failing test, write one now and watch it fail for the right reason. **Commit the test before writing any implementation code** — a standalone test commit is the rollback anchor: `git reset --hard <test-commit>` discards a bad implementation attempt cleanly without losing the test. If you cannot write the failing test, the task is under-specified — escalate, don't improvise. (UI/visual tasks: write the manual validation step instead.)
3. **Implement** to the standards in `docs/engineering-standards.md`. Match surrounding code's idiom; reuse existing utilities — search before writing a helper.
4. **Verify:** run the project's verify command (CLAUDE.md § Conventions). Fix until green. Same error surviving 3 distinct fix attempts → stop, write a diagnosis (what you tried, current hypothesis), escalate.
5. **Commit:** 1–3 sentences, what + the non-obvious why. Tick the task in the issue checklist (`gh issue edit` or close the sub-issue).

## Hard rules

Read `references/guardrails.md` before step 3 the first time, and whenever tempted to bend one. The unbendable three: never weaken/delete/skip a test to make it pass; never add `# noqa` / `# type: ignore` / skip-markers without an adjacent justification comment; never add a dependency without surfacing it first.

## Local-LLM routing (default executor when Ollama is available)

For tasks rated **mechanical or standard** by default; complex tasks are eligible when committed tests fully pin the behavior (see `references/local-llm.md`). When Ollama is available this is the **default** executor; without it, fall back to a sonnet subagent. The standalone `--local` flag forces this path for a one-off task. Process in `references/local-llm.md`; mechanics in `scripts/local_task.py`. **Every local run is followed by a mandatory top-model review of the diff before commit** — never commit unreviewed local output — and logged to `.local-llm-log.jsonl` so the economics stay decidable.
