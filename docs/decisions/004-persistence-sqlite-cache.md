# ADR-004: SQLite with a TTL place-cache separate from durable tables

Status: accepted · Date: 2026-06-12

## Context

A local single-user app must persist trips, the interest library, ratings, anchors, and the last few schedule versions, and reopen them later. [ADR-001](001-place-data-source.md) imposes a hard constraint: Google Places coordinates/hours may **not** be cached beyond 30 days, though `place_id` may be stored indefinitely. The store must respect that while supporting save/reopen and versioning.

## Options considered

1. **SQLite + repository, with a separate TTL place-cache.** Durable tables hold user-owned data; a distinct `place_cache` table holds perishable place details with a `fetched_at` timestamp, evicted/re-fetched per TTL. Durable rows reference `place_id` only.
   - Pros: ToS-compliant by construction (durable data never includes coordinates); real query/versioning support; zero-config, file-based, ships with Python.
   - Cons: reopening a trip needs network to re-hydrate place details; a (light) schema/migration discipline is needed.
2. **JSON files on disk.** One file per trip.
   - Pros: dead simple, human-readable.
   - Cons: no querying, awkward versioning and cache eviction, easy to accidentally persist coordinates durably (ToS risk); concurrent-write footguns.
3. **Store full place data durably** (in any store). Rejected outright — violates ADR-001's caching ban.

## Decision

**SQLite** via a `services/repository/` module. **Durable tables:** trips, interests (library), trip-interest activations, ranked_places (rating + duration override), fixed_anchors, schedule_versions (serialized itinerary JSON, last 3 per trip). **Evictable cache:** `place_cache(place_id, name, category, coords, hours, rating, price, fetched_at)` with TTL eviction and re-fetch on access. Schema ships as a package resource (`services/repository/schema.sql`).

## Consequences

- The 30-day rule is enforced structurally: durable rows carry `place_id`; coordinates/hours live only in the evictable cache. A trip reopened after the TTL re-fetches live data (needs internet) — consistent with the PRD persistence flow.
- Versioning is cheap (a schedule version is one serialized JSON row; keep last 3).
- A migration approach for schema evolution is deferred to implementation (candidate: simple versioned SQL scripts); not needed for milestone 0.
- JSON rejected for weak querying/versioning and the ease of accidentally violating ADR-001.
