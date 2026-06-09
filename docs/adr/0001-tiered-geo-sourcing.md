# Tiered geo sourcing, with Gemini as namer-of-last-resort

Every Option needs a location and pairwise travel times for the scheduler to avoid
zig-zagging. We resolve geography through a cascade behind a `GeoProvider` /
`TravelProvider` interface:

1. **Google Maps APIs** (Places geocoding + Distance Matrix) — most accurate, used
   when a key is configured.
2. **OpenStreetMap stack** (Nominatim geocoding + OSRM/haversine travel) — free
   fallback, keeps the app runnable with no paid key.
3. **Gemini-estimated geo** — when Gemini proposes Options it also returns its
   best-guess coordinates; these are the last resort when both lookups fail.

Gemini is treated as a *namer of places*, not a trusted source of geography — its
coordinates are used only when nothing better is available, and travel time is then
derived from straight-line distance plus a speed heuristic.

## Considered Options

- *Pure LLM geo* — rejected: hallucinated coordinates make the anti-zigzag guarantee
  meaningless.
- *Google-only* — rejected as a hard dependency: breaks "runs locally" without a key.

## Consequences

- A cross-cutting constraint shapes the whole design: **minimise LLM calls and
  tokens.** Because Gemini already returns coordinates with each Option, we avoid a
  separate geo round-trip in the common case, batch Interests into as few calls as
  possible, and cache aggressively. Provider tiers are individually mockable in tests.
