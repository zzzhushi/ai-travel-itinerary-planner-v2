# ADR-001: Use a structured place-data API as source of truth, with the LLM as curator

Status: accepted · Date: 2026-06-12

## Context

The planner must show *real* places (existence, coordinates, opening hours, rating/price) and feed a **deterministic scheduler** that needs machine-readable lat/lng and hour windows. The user also wants the most up-to-date info on what to do, and the app runs locally with Gemini as its LLM under a free-tier (~$0) cost ceiling. The question: where does place data come from? (Researched June 2026; pricing is illustrative and must be re-verified before build.)

## Options considered

1. **Google Places API (New)** as source of truth (+ Routes API for travel time later).
   - Pro: only option returning structured coords, `regularOpeningHours`, rating, and price in one call. Best freshness/coverage. Hobby use likely ~$0 within free caps.
   - Con: requires a Google Cloud billing account + key; **ToS forbids caching coordinates beyond 30 days** (place IDs may be stored indefinitely); per-SKU quotas to manage.

2. **Gemini with Google Maps/Search grounding** as source of truth.
   - Pro: live, high-coverage discovery; minimal plumbing; returns real place IDs.
   - Con (decisive): returns **prose + place IDs only — no structured coordinates or machine-readable hours**. Cannot drive a deterministic scheduler on its own; you must still hydrate every place via Places Details, and it bills per grounded prompt on top.

3. **OpenStreetMap (Overpass), optionally + Foursquare.**
   - Pro: structured coords and an `opening_hours` tag; OSM's ODbL license permits durable local caching (with attribution/share-alike) — the only option you can fully keep offline. Free.
   - Con: `opening_hours` is sparsely populated; no ratings/price. Foursquare can backfill but its license forbids derivative works and long caching — hostile to local persistence.

## Decision

Use **Google Places API (New) as the source of truth** for place existence, coordinates, hours, rating, and price. Use **Gemini as the discovery/curation brain** (optionally with Maps grounding to propose places and return place IDs, which are then hydrated via Places Details). Keep **OSM/Overpass as the degradation fallback** and as the one source whose data may be durably cached. Travel time in v1 is local haversine (no API); Google Routes is a v2 upgrade.

This choice is **accepted** at the `/milestones` architecture gate; live-pricing verification remains a blocking pre-build task (tracked in the PRD open questions), and an OSM-only fallback architecture is the recorded escape hatch if Google cost/ToS friction proves too high.

## Consequences

- **Persistence is shaped by the caching ban:** store only place IDs + user data durably; treat coordinates/hours/ratings as a ≤30-day refreshable cache and re-fetch when a trip is reopened (so reopening needs internet). This is why the PRD's persistence model stores IDs, not full place records.
- **Setup cost:** the operator must create a Google Cloud billing account and key even to use the free tier; the app needs a spend guard to keep within ~$0.
- **Grounding is a discovery aid, not a data source** — any use of Gemini grounding still requires Places Details hydration.
- **Revisit if** Google cost/ToS friction grows: the OSM-only path (accepting sparse hours, no ratings) becomes the fallback architecture, and a superseding ADR would record that switch.
