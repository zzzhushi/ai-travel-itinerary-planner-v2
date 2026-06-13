# API / Operation Contract

The **use-cases are the API**. Every operation below is one `application/` use-case, invoked by the CLI (M1–M6) and the web app (M7) alike — one contract, two front doors. This pins the shape of the flow before either delivery surface is built. HTTP paths are the web binding; the CLI column is the equivalent command.

This is a design artifact, not a frozen spec — request/response *fields* firm up in implementation; the operations, error semantics, and status codes are the stable part.

## Resources

`Trip` · `Interest` (library) · `Suggestion` (candidate place for an interest) · `RankedPlace` · `ScheduleVersion` (a routed itinerary) · `Anchor`.

## Operations

| # | Operation | HTTP | CLI | Input → Output |
|---|---|---|---|---|
| 1 | Create trip | `POST /trips` | `trip new` | city, dates, arrival/departure, lodging, pace, meal toggle, filters, walking tolerance → **201** `Trip` |
| 2 | List / get trips | `GET /trips` · `GET /trips/{id}` | `trip list` · `trip show` | → **200** `Trip[]` / `Trip` (re-hydrates cached place data if TTL-stale) |
| 3 | Interest library | `GET /interests` · `POST /interests` | `interest list` · `interest add` | free-text prompt (+optional category) → **200/201** `Interest` |
| 4 | Activate interests | `POST /trips/{id}/interests` | `trip interests` | interest ids/prompts → **200** `Trip` |
| 5 | Gather suggestions | `POST /trips/{id}/suggestions` | `trip suggest` | (none) → **200** `{interest_id: Suggestion[]}` — fetch + LLM fit-filter |
| 6 | Submit ratings | `PUT /trips/{id}/ratings` | `trip rate` | `{place_id: {rating 1–5, duration_override?}}` → **200** `Trip` |
| 7 | Build schedule | `POST /trips/{id}/schedule` | `trip schedule` | (none) → **201** `ScheduleVersion` **or 409** feasibility pushback `{fits, requested, over_by, suggestions[]}` |
| 8 | List / get versions | `GET /trips/{id}/versions` · `/versions/{v}` | `trip versions` | → **200** `ScheduleVersion[]` / one (last 3 kept) |
| 9 | Revert version | `POST /trips/{id}/versions/{v}/revert` | `trip revert` | → **201** new current `ScheduleVersion` |
| 10 | Refine | `POST /trips/{id}/refine` | `trip refine "<text>"` | `{feedback}` → **201** new `ScheduleVersion` **or 409** pushback. LLM turns text into edits; deterministic re-solve produces the version |
| 11 | Refresh place data | `POST /trips/{id}/refresh` | `trip refresh` | (none) → **200** `Trip` — re-fetch coords/hours past cache TTL |
| 12 | Export | `GET /trips/{id}/export?format=md\|map` | `trip export` | → **200** file (Markdown itinerary / static map PNG) |

## Status codes

| Code | When |
|---|---|
| 200 / 201 | success / resource created |
| 400 | malformed request |
| 404 | unknown trip / interest / version |
| 409 | **schedule infeasible** — must-sees over-commit, or a place closed on all available days; body carries the pushback numbers |
| 422 | semantically invalid (e.g. departure before arrival) |
| 429 | free-tier quota would be exceeded — `QuotaGuard` refused before billing |
| 424 / 502 | upstream place/LLM provider failed; if a fallback (OSM) succeeded the response is **200** with `outcome: degraded` |
| 503 | all place sources down — nothing to fall back to |

## Notes that shape the use-cases

- **409 is a first-class outcome, not an error** — the deterministic feasibility check returns the pushback body; both CLI and web render it and let the user re-rank, then retry build.
- **Degradation is visible** — a response sourced from the OSM fallback (or with unverified hours) carries an `outcome: degraded` / per-place `hours_unverified` flag rather than failing.
- **Refine (10) reuses Build's machinery** — it is "produce edits → re-solve → new version," so it shares the schedule/feasibility path and the 409 semantics.
- **The CLI ships first** and implements operations 1–10 over M1–M6; the web app (M7) binds the same use-cases to these HTTP routes; export/map (12) completes at M8.
