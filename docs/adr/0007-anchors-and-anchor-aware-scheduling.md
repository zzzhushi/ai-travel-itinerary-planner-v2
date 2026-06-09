# Anchors: Home Base, Pinned Commitments, and anchor-aware scheduling

Two kinds of fixed points constrain a day, and the scheduler builds the day around both
(extends [ADR-0005](./0005-deterministic-travel-aware-scheduler.md)).

- **Home Base** — the trip's lodging. Every day's Schedule starts and ends here and travel
  to/from it counts. This closes a real gap in the original design, where only Day 1 was
  anchored (at arrival) and days 2..N had no defined start/end location. **One Home Base per
  trip; multiple/changing lodgings are deferred** (with multi-city — see PRD Future).
- **Pinned Commitment** — a fixed time + place item the traveller must attend. **One concept
  unifies three requested features:** a user-added fixed event (wedding), a timed/locked
  ticket, and a flight-as-event. The scheduler places a pin at its exact time and routes the
  day around it; **regeneration never moves a pin**, and the validator asserts this.

**Anchor-aware clustering.** Anchors (Home Base, Pinned Commitments, long-duration Options)
exert spatial gravity: when the day already fixes you in an area for a while (e.g. 3h at a
theme park), the scheduler prefers to fill adjacent slots with nearby Chosen Options rather
than crossing the city and back. This sharpens — does not replace — the travel-aware
objective of ADR-0005: `w_travel` is evaluated around fixed points, not over a free ordering.

## Scope

- **Home Base enters the MVP** (set at trip setup, geocoded via the tier ladder of
  [ADR-0001](./0001-tiered-geo-sourcing.md)).
- The **Pinned Commitment seam is built into the scheduler's input contract from the start**
  so adding it is not a later rewrite, even if the full UI for adding pins lands post-MVP.
- The validator gains checks: pins scheduled at exact time and unmoved across regenerations;
  every day begins and ends at Home Base.

## Consequences

- **Flights stay only partially modeled:** a flight is a Pinned Commitment *plus* an
  airport↔Home Base transfer. Full transfer handling and mid-trip flights are **deferred**
  (they travel with multi-city support).
- Locking a scheduled Option = turning it into a Pinned Commitment at its current time.
