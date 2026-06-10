# Handoff — AI Travel Itinerary Planner

Date: 2026-06-09
Branch: `skillstest/prd/satyajanghu`
Owner: zzzhushi

For the next session: this is where we are, what exists, and what to do next.

---

## What we did this session

Ran a deep requirements interview and turned a high-level idea into an actionable PRD.
**No application code yet** — this was a planning/spec session. Output is three docs in `/docs`.

Artifacts produced:
- **[docs/prd.md](prd.md)** — the full PRD (problem → architecture → scheduler → LLM model →
  persistence → API → telemetry → testing → milestones). Internally consistency-checked.
- **[docs/logging.md](logging.md)** — OpenTelemetry-based diagnostics design + the event catalog (stub).
- **[docs/grill-log.md](grill-log.md)** — the distilled decisions and the *why* behind each.

---

## Current state

- **Phase:** planning complete; ready to start building **V1**.
- **Repo:** only docs + skill files; no Python package, no tests yet.
- **PRD status:** Draft v1, consistent. A handful of small open questions remain (PRD §19) —
  none block V1–V2.

---

## The decisions that drive everything (don't re-litigate)

1. **Hybrid data:** LLM *proposes* places; deterministic code *validates/enriches* against
   real geodata (Nominatim) before anything enters a schedule. Kills hallucination.
2. **Anchor primitive:** hotel / flights / tickets / events / buffers / user-locks are all
   one thing — fixed/soft/temporary anchors. The scheduler builds around them.
3. **LLM ↔ scheduler contract:** LLM turns *words → numbers once*; the **deterministic**
   scheduler optimizes the numbers every time. Preferences arrive as weights/constraints.
4. **Objective:** weighted sum, defaults **interest > travel > pace**, exposed as tunable
   levers. (Recorded tension: this ranks interest above the original "don't criss-cross" pain.)
5. **Not agentic:** discrete, single-shot, schema-constrained LLM calls (Curator + Editor).
   ~1 call to plan, ~6 per session. Geometry levers cost 0 calls; only content changes are metered.
6. **Degradation floor:** cache → deterministic Overpass-only mode. Always produces something real.
7. **Architecture:** pure-Python tested engine → FastAPI (localhost) → CLI (v1) → NiceGUI map UI (v2).
8. **Persistence:** files for trip state + versions; SQLite for the response cache; JSONL for logs. No server DB.
9. **Telemetry:** OpenTelemetry (traces = primary), custom JSONL exporter, optional OTLP→Jaeger/Tempo.
   `request_id == run_id == trace_id` — one id ties API ↔ engine ↔ trace for agent debugging.
10. **Testing:** invariant/property tests gate CI; LLM responses cached for determinism;
    quality is human-judged (LLM-judge out of scope). Replay-from-run-dir is the headline acceptance test.

---

## Next steps (start here)

**V1 — Walking skeleton** (per PRD §16): the thin end-to-end path that *plans a trivial trip*,
not just scaffolding. From a minimal `trip.yaml` → real geocoded Markdown+JSON itinerary.
- Python 3.11+ package layout + CLI entry (`plan trip.yaml`); Pydantic v2 schemas for
  `trip.yaml`, `Anchor`, `Place`, `Preferences`, itinerary/version.
- `trip.yaml` loader + validation; Gemini key/config.
- Per-trip **file store** (`trips/<trip_id>/`) with version snapshots.
- **SQLite** response cache (per-adapter keys).
- **OTel-backed JSONL logger** emitting the event catalog in `docs/logging.md`
  (`runs/<trip_id>/<run_id>/manifest.json` + `trace.jsonl`).
- One **Curator** LLM call + **Nominatim** geocode; **naive day-fill** scheduler (no
  travel/anchors yet); Markdown+JSON output.
- CI + the **invariant-test harness** (fixtures with mocked geodata).

Then **V2** (geographically-sane days: clustering, two-tier haversine travel, hotel-anchored
ordering, hard constraints, move-then-drop, explainer) — the heart, fully testable with zero
external calls. Anchors + pacing follow in **V3**.

---

## Open questions to resolve as you build (PRD §19)

- Exact ORS free-tier matrix/directions limits → set per-day call caps.
- Concrete pace → stops/day mapping (e.g. relaxed 3–4, balanced 5, packed 6–7).
- Per-day vs per-slot regeneration in v1 (start per-day).
- Default candidate over-fetch count per category (start ~8).
- Version-history retention/pruning policy + owner.
- Exactly how/where the user flags must-sees in the spec.

---
