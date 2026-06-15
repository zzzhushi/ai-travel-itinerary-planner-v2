# ADR-007: Travel-time estimates rounded up to the nearest 15 minutes

Status: accepted · Date: 2026-06-14

## Context

`haversine_minutes` returns straight-line distance ÷ assumed walking speed. This
systematically **underestimates** real travel time: it ignores roads and detours,
transit wait times, the overhead of leaving a venue and orienting, and any
pace variation. An itinerary built on raw haversine minutes looks unrealistically
precise ("leave at 10:03") and breaks the moment a user walks slightly slowly,
takes a wrong turn, or lingers an extra minute at a stop.

## Options considered

1. **Raw minutes** (prior behaviour) — use `round(hours * 60)`. Simple, but
   produces false precision and itineraries that are fragile to small deviations.
2. **Ceiling to nearest 15 minutes** — `math.ceil(raw / 15) * 15`. Matches how
   people naturally think about travel ("about 15 minutes", "half an hour").
   Adds a meaningful buffer without being arbitrary. Same-location stays 0.
3. **Flat buffer** (e.g. always +10 min) — easy but ignores that short trips need
   more *relative* buffer than long ones; a 2-min walk +10 is 12 min, while a
   30-min walk +10 is 40 min — inconsistent mental model.
4. **Configurable multiplier** (e.g. `× 1.3`) — proportional, but fractional
   results still create false precision and require an arbitrary constant.

## Decision

**Ceiling to the nearest 15 minutes.** It maps to the mental model travellers
actually use, provides a consistent buffer at all distances, and keeps the output
readable (times land on :00, :15, :30, :45). The consequence is a slightly more
conservative day — a densely packed itinerary may fit one fewer stop — which is
the right tradeoff: a realistic plan beats an optimistic one that fails on the
ground.

## Consequences

- Travel time between any two distinct locations is always ≥ 15 minutes.
- Day capacity is modestly reduced; tests that assert exact stop counts or travel
  totals must account for 15-minute granularity.
- When the travel function is swapped for Google Routes API (ADR-003 swap path),
  the rounding should be revisited — real transit times from a routing API already
  incorporate buffers and may not need additional ceiling.
