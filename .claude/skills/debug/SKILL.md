---
name: debug
description: Systematic hypothesis-driven debugging for any unexpected failure — broken demo, failing test, weird behavior, production error. Use whenever the cause of a failure is unknown ("why is this failing", "this worked yesterday", "weird bug").
---

# Debug: Hypothesis-Driven, Reproduce-First

The discipline exists because the default failure mode — pattern-matching the symptom to a familiar cause and "fixing" that — produces fixes for bugs you don't have while the real one survives.

## The loop

1. **Reproduce first.** A failure you can't reproduce on demand cannot be verified fixed. Get the smallest deterministic reproduction (ideally a test). If it's intermittent, make reproduction itself the first investigation: what varies between runs (timing, ordering, state, environment)?
2. **Read the actual error.** The full traceback, the real log lines (this codebase's structured logs carry request/correlation ids — follow one failing request end to end). Not a paraphrase from memory of similar errors.
3. **State a hypothesis precisely enough to be wrong:** "X is None here because the cache returns stale entries after Y" — not "something's wrong with the cache". Write it down.
4. **Test the hypothesis with the cheapest decisive observation** — a targeted log line, a debugger breakpoint, a 3-line scratch script — *before* writing any fix. Change one variable at a time; if you change two things and it works, you've learned nothing durable.
5. **Confirmed → fix the cause, not the symptom.** Guarding `None` where it crashed is symptom-patching if the real question is why it was `None`. Refuted → back to 3 with what you learned. Three refuted hypotheses → widen: question an assumption you marked "can't be it" (it usually is).
6. **Lock it in:** the reproduction becomes a regression test that fails on the old code and passes now. Remove scratch logging. If the bug revealed a missing log line that would have made this diagnosable from logs alone (the standards bar), add that log line permanently.

## Rules

- Never fix what you can't reproduce; never declare fixed what you haven't re-run.
- `git diff` / recent commits are evidence, not suspicion — "what changed since it last worked" is often the cheapest decisive observation (use `git bisect` when the range is wide).
- If the fix touches shared state, config, or infrastructure, verify the evidence supports *that specific* action before acting — a symptom matching a known failure may have a different cause.
- Cap: if 3+ hypotheses die and you're guessing, stop and write up the state (repro, evidence, dead hypotheses) for the user — that document is valuable; thrashing isn't.
