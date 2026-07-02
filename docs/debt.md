# Tech-debt ledger

Deferred and disputed review findings land here (guardrail 11), never in PR-comment
limbo. One line per item. **Promotion rule: 3rd sighting → the item becomes a real
task in the next milestone** (`/milestones` Gate 2 reads this file when slicing —
no judgment call needed). Fixed items are deleted, not struck through.

A "sighting" = any review, audit, or implementation session that independently
flags the item. Bump the count and add the source when it happens.

| debt | where | first seen | sightings | promote when |
|---|---|---|---|---|
| `TravelMinutes` type alias defined in 4+ places | `domain/scheduler.py`, `domain/clustering.py`, `domain/planner.py`, `domain/feasibility.py` (+ `TravelFn` in `application/build_schedule.py`) | PR #25 review | 2 (PR #25, M3 reviews) | 3rd sighting → consolidate into `domain/models.py` |
| `_hhmm` helper duplicated | `cli.py`, `web/routes/schedule.py` | PR #25 review | 1 | 3rd duplicate site appears |
| Feasibility double-build: `check_feasibility` runs `schedule_trip`, then `build_schedule` runs it again on the 201 path | `web/routes/schedule.py` POST /schedule | PR #31/#33 reviews | 1 | place counts grow past fixtures (M5 real data) or p95 latency budget set |
| Anchored days skip 2-opt (anchor path is greedy-only per segment) | `domain/scheduler.py` `_schedule_with_anchors` | PR #31 review | 1 | route quality complaint on an anchored day, or M7 refine loop needs it |
| `response_model=None` drops the 201 schema from OpenAPI | `web/routes/schedule.py` POST /schedule | PR #33 review | 1 | first external consumer of the OpenAPI spec (M7 web UI) |
| Silent empty day when `arrival_min > day_end_min` (all places land in unscheduled, no explanatory error) | `domain/budgets.py` `day_windows` | PR #25 review | 1 | M4 validation layer lands (422 semantics exist to express it) |
| Walking-cap trim is O(N²) schedules per day | `domain/planner.py` `_schedule_day_within_cap` | PR #25 review | 1 | >~30 places/day becomes a real input (M5 real data) |
