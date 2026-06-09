# LLM-based, travel-aware scheduler with a deterministic validator

The Schedule is produced by **Gemini**, not a deterministic algorithm — scheduling
need not be reproducible. To keep the headline anti-zigzag feature real and the work
testable, the LLM is constrained and checked:

- **Input:** the LLM receives the chosen Options *plus the real travel-time matrix*
  (ADR-0001) and the constraints/preferences. It does not guess geography.
- **Output:** a structured Schedule (day/order/time per Option) parsed into
  `schedule`/`schedule_item`.
- **Validator (deterministic):** a Python checker scores each Schedule — total travel
  minutes per day, opening-hours violations, meal-slot fit, zig-zag detection. It powers
  diagnostics logging, **property-based tests** ("no opening-hours violations", "day
  travel under threshold"), and an optional **re-prompt** when a Schedule scores poorly.

We retire the phrase **"planner-aware"** in favour of **travel-aware scheduler**: the
scheduler considers every chosen Option across all days, informed by the travel matrix,
to minimise back-and-forth.

Preferences are expressed two ways:

- **Hard constraints** (in the prompt *and* enforced by the validator): opening hours,
  meal-time windows for Food, daily start/end window, day-1 start at `arrival_at`, visit
  durations, pace caps, transport mode (selects the travel-time matrix).
- **Soft preferences** (prompt guidance + validator scoring weights): `w_travel`
  (anti-zigzag), `w_rank` (the user's Option rankings), `w_balance` (category mix vs
  theme-days), `w_pace`.

## Considered Options

- *Deterministic algorithm (clustering + 2-opt)* — rejected by author preference for an
  LLM-driven approach; non-determinism is acceptable.
- *Pure LLM from its own geographic knowledge* — rejected: unreliable travel-awareness,
  wastes the geo matrix, and is hard to test.
- *LLM with no validator* — rejected: leaves the anti-zigzag goal and tests unenforceable.

## Consequences

- Scheduling output varies run-to-run; tests assert *properties* via the validator, not
  exact layouts. The validator is the contract between "LLM creativity" and the
  guarantees the product promises.
- Adds tokens per schedule (and more on re-prompts); mitigated by scheduling only chosen
  Options and capping re-prompt attempts.
