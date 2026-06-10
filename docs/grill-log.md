# Grill: AI Travel Itinerary Planner
Date: 2026-06-09

## Intent
Build a locally-run, Python, LLM-assisted tool that turns a traveller's city + dates +
anchors + preferences + interests into a realistic, geographically-sane, day-by-day
itinerary they can refine. Portfolio-grade: clean engine, tested, with a real API and a
simple map UI. The output of this interview is a PRD an engineer can act on without
follow-up.

## Constraints
- Runs locally = **no hosted backend of ours**. External APIs allowed only if **free-tier
  with usable limits**; the only required secret is the Gemini key.
- Python; LLM = Gemini (`flash-lite`) to start.
- **Automated tests** and **diagnostics logging** are hard requirements.
- Everything needs a fallback (LLM, geocoding, routing).
- Minimize LLM/API calls to stay inside free tiers.
- Owner doesn't want to learn frontend (rules out React).

## Key decisions
- **Data: hybrid.** LLM proposes candidate places; deterministic code validates/enriches
  each against real geodata (Nominatim) before it may enter a schedule. *Why:* keeps it
  local-capable while killing hallucination — every scheduled place resolves to real coords.
  *Rejected:* LLM-only (stale/hallucinated, no real travel time); pure-API (loses taste).
- **Degradation floor = deterministic mode.** Cache → Overpass-tagged places + deterministic
  scheduler. *Why:* honest "needs a fallback" — product works with zero AI because all
  load-bearing logic is deterministic. *Rejected:* cache-only (fails on new city); local
  Ollama (scope creep → future).
- **Anchor primitive.** Hotel/flights/tickets/events/buffers/user-locks unified as anchors
  (fixed / soft / temporary). *Why:* one mechanism handles day-1 arrival truncation, fixed
  events, ticketed activities, and "lock what I like" with no special-casing.
- **LLM ↔ scheduler contract.** LLM converts words→numbers once (scored, structured places);
  scheduler is deterministic and optimizes the numbers. *Why:* resolves "how can a no-LLM
  scheduler honor preferences" — preferences arrive as weights/constraints/scores. Also makes
  geometry tuning free and tests deterministic.
- **Objective = weighted sum**, defaults **interest > travel > pace**, exposed as tunable
  levers. *Why:* owner ranked interest-match above travel-tightness (accepted tension with the
  "criss-crossing" problem statement). Levers split into **deterministic** (interest/travel/
  pace weights → free, instant re-solve) vs **content** (local↔touristy → metered LLM call).
- **Must-sees = near-hard:** move-then-drop, always surface the reason (explainability layer).
- **Two-tier travel.** ORS *matrix* for planning (~1–2 calls/city, accurate in barrier
  cities); short hops ≤ walk_threshold use a free walk estimate; haversine is the universal
  fallback. Real street *polylines* are display-only, fetched **on-demand** for finalized
  legs and used to re-validate timing. *Why:* accuracy where it matters, near-zero cost.
- **No agents — discrete structured calls.** Roles: Curator (1 batched call/trip), Editor
  (on-demand), optional Narrator. *Why:* agentic loops make call count unpredictable and
  untestable and threaten the free tier. Typical session ~6 calls.
- **Architecture:** pure-Python tested engine → FastAPI (localhost) → CLI (v1) → NiceGUI
  drag+map UI (v2). *Why:* engine/tests are stack-independent; UI is deferrable/swappable.
  *Rejected:* Streamlit (weak drag, mirrors CLI), React (owner won't learn frontend).
- **Map = read-only**, colored/numbered by day; rating in a separate pane with map highlight;
  no connecting lines in v1. *Why:* drag-on-map is fiddly; list-drag + map-mirror is cleaner.
- **Quality = human-in-the-loop** via locks + levers + feedback + version history; targeted
  per-day/per-slot regeneration. **LLM-as-judge out of scope.**
- **Testing:** invariant/property tests gate CI (engine contract); LLM responses cached for
  determinism; golden tests only for deterministic transforms.
- **Scope:** single city, single party, 1–14 days; fixed interest set + user-defined.

## Surfaced assumptions
- "Local" tolerates one hosted dependency (Gemini) — so it means "no server to deploy," not
  air-gapped.
- OSM coverage is adequate for target cities (flagged as medium risk; confidence logged).
- Owner values *more of what I love* over *minimum walking*, despite the stated core pain
  being criss-crossing — made explicit and made tunable.

## Open questions
- Exact ORS free-tier matrix/directions limits at build time (set per-day caps; verify).
- Concrete pace → stops/day mapping (relaxed/balanced/packed).
- Per-slot regeneration in v1 or per-day only (start per-day).
- Default over-fetch count per category (start ~8).

## Out of scope (v1)
Multi-city; multi-person preference reconciliation; booking / live availability; LLM-judge
quality eval; local Ollama fallback; React UI / full map manipulation; paid APIs.
