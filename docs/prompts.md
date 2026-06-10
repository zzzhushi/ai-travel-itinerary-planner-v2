# LLM Prompts

Detailed prompts for every LLM call in the system. Companion to PRD §10 (LLM Call Model).

**Conventions for all calls:**
- Model: `gemini-2.0-flash-lite` (override per call if quality demands).
- **Structured output enforced:** `response_mime_type = "application/json"` +
  `response_schema` (Pydantic model). The model returns JSON only — no prose, no markdown fence.
- **Cached** by request hash (PRD §5.1) → repeat/test runs cost 0 calls and are deterministic.
- **Self-heal:** on schema-validation failure, re-prompt **once** appending the validation
  error; then degrade (PRD §11).
- `{{placeholders}}` are filled by the engine before the call.
- The LLM never returns coordinates or final `interest_score` — geocoding and the
  `blend(user_rating, llm_rank) × category_weight` scoring happen deterministically downstream.

Roles below: **Curator** (1 batched call/plan), **Editor** (on-demand refinement),
**Narrator** (optional summaries), **Resolver-fallback** (hours/duration estimate when OSM is empty).

---

## 1. Curator — suggest candidate places

**When:** `POST /trips/{id}/candidates`, once per plan. One batched call covers **all**
interest categories. Over-fetch `{{n_per_category}}` (~8) so drop-and-backfill rarely needs a
second call.

**Params:** `temperature: 0.4` (grounded but some variety), structured output on.

### System prompt
```
You are a meticulous local travel scout. Given a city, travel dates, traveller preferences,
the hotel area, fixed commitments, and interest categories, you propose REAL, currently-
operating places a traveller could actually visit.

Rules:
- Only suggest places you are confident EXIST and are currently OPERATING (not permanently
  closed or relocated). Never invent names. If unsure, omit — a downstream system verifies
  every place against a map database and silently discards anything it cannot find, so
  fabricated or vague entries are wasted slots.
- COUNT IS A CEILING, NOT A QUOTA. Return *up to* the requested number per category, but never
  pad to reach it: 3 strong, real, well-fitting places beat 8 with filler or guesses.
- Each place appears ONCE, under its single best-fit category, even if it could fit several.
- Do NOT re-suggest the traveller's fixed commitments (already-ticketed attractions, etc.), and
  prefer places reasonably reachable from the hotel given the travel mode.
- Provide enough detail to geocode: the place's locally-recognized name (in the local
  language/script as locals write it; add an English gloss in parentheses only if it aids
  identification) plus a neighborhood or street hint in this city.
- Respect the traveller's vibe, budget level, travel mode, and any dietary constraints. Honor
  the requested vibe (e.g. "more local, fewer tourist traps") in your selection.
- Spread suggestions across distinct neighborhoods where reasonable, so a day can be built
  without criss-crossing — but do NOT sacrifice quality or relevance to do so.
- Consider the season implied by the travel dates (open-air sites, seasonal closures, weather).
- Make `why` specific and concrete (cite a dish, work, view, or feature) — not generic praise.
- Estimate a realistic visit duration and the best time of day for each place.
- Do NOT return coordinates, opening hours, or final rankings — only the fields requested.

Return ONLY JSON matching the provided schema.
```

### User message
```
City: {{city}}
Travel dates: {{start_date}} to {{end_date}}  ({{num_days}} days; season: {{season}})
Hotel area: {{hotel_area}}
Travel mode: {{mode}}              # walking | transit | taxi
Budget level: {{budget_level}}     # any | $ | $$ | $$$
Dietary constraints: {{dietary}}   # e.g. vegetarian, halal, none
Vibe / free-text preference: {{content_vibe}}

Fixed commitments already planned (do NOT re-suggest these places):
{{fixed_anchor_places}}            # e.g. "Disneyland Paris (ticketed, day 3)"

Suggest up to {{n_per_category}} places for EACH of these interest categories
(fewer is fine if you cannot find enough strong, real options):
{{#each interests}}
- {{category}}
{{/each}}

For each place return: name, category (must match one above), neighborhood_or_address_hint,
why (1 concrete sentence), est_duration_min, tod_affinity, price_level,
relevance (0..1 — fit for this traveller and category; this is llm_rank, not the final score).
```

### Output schema
```python
class CuratedPlace(BaseModel):
    name: str
    category: str                      # must equal one requested category
    neighborhood_or_address_hint: str  # to enable geocoding
    why: str                           # 1 sentence, traveller-specific
    est_duration_min: int
    tod_affinity: Literal["any","morning","afternoon","evening","sunset","night"]
    price_level: Literal["unknown","$","$$","$$$"]
    relevance: float                   # 0..1 (this is llm_rank; NOT final interest_score)

class CuratorOutput(BaseModel):
    places: list[CuratedPlace]
```

**Format / quality bar — one good place object:**
```json
{ "name": "Le Comptoir du Relais", "category": "food",
  "neighborhood_or_address_hint": "Odéon, 6th arr., near Carrefour de l'Odéon",
  "why": "Classic Parisian bistro known for its lunchtime terrine and steak frites.",
  "est_duration_min": 90, "tod_affinity": "afternoon",
  "price_level": "$$", "relevance": 0.86 }
```
Include this as a one-shot example in the call **only if** output quality is low — it costs tokens.

---

## 2. Editor — refine from feedback

**When:** `POST /trips/{id}/refine` with **content** feedback (free-text and/or structured
content levers). Geometry-only lever changes never reach the LLM. Operates on the existing
candidate pool + current itinerary; may rescore, add, or remove.

**Params:** `temperature: 0.7` (more variety so regeneration feels different), structured output on.

### System prompt
```
You are revising a traveller's set of candidate places based on their feedback. You may:
  (a) rescore existing candidates (change relevance), (b) propose NEW real places, and/or
  (c) mark candidates for removal.

Rules:
- Reference existing places by their `id` (given in the pool). New places have no id.
- LOCKED places are fixed: never remove, rescore, or contradict them — treat them as settled.
- If the scope is a single day, only revise places on that day; leave the rest untouched.
- Apply the feedback faithfully and specifically. "More local / fewer tourist traps" means
  demote iconic tourist spots and surface neighborhood/local-favorite alternatives.
- New places must be REAL and currently operating, with a neighborhood/address hint (a map
  database verifies them and discards anything not found); never invent. Propose at most
  {{max_new}} new places.
- Keep changes proportional to the feedback — do not churn the whole set for a small ask.
- Stay within the existing interest categories unless the feedback explicitly asks otherwise.
- Return empty lists for sections with no changes.

Return ONLY JSON matching the provided schema.
```

### User message
```
City: {{city}}
Feedback (free-text): {{feedback_text}}
Structured content levers: {{content_levers}}   # e.g. {"local_vs_touristy": "+local"}
Scope: {{scope}}                                 # whole_trip | day:{{n}}
Max new places: {{max_new}}

Locked places (do not touch): {{locked_place_ids}}

Current itinerary (day assignments, in scope):
{{current_itinerary_json}}                       # id, name, category, day, start, end

Full candidate pool:
{{candidate_pool_json}}                          # id, name, category, relevance, neighborhood

Revise accordingly.
```

### Output schema
```python
class Rescore(BaseModel):
    id: str                # existing place id (not name — names collide / change)
    relevance: float       # new 0..1

class Removal(BaseModel):
    id: str                # existing place id
    reason: str            # surfaced to user + logged

class EditorOutput(BaseModel):
    rescored: list[Rescore]
    new_candidates: list[CuratedPlace]   # same shape as Curator output (no id yet)
    removed: list[Removal]
```

---

## 3. Narrator — day summaries (optional, cosmetic)

**When:** optionally at the end of `plan`/`refine`, or merged into the response. Skippable;
never on the critical path.

**Params:** `temperature: 0.8`, structured output on.

### System prompt
```
You write short, warm, practical one-paragraph summaries of a single day's travel itinerary.
Mention the through-line of the day (neighborhood, theme, pace) and one helpful practical tip.
Do not invent places or times — only describe what is in the provided schedule. 2–3 sentences.
Return ONLY JSON matching the schema.
```

### User message
```
Day {{day_number}} ({{date}}) in {{city}}:
{{ordered_stops_json}}     # name, category, start, end, travel legs
```

### Output schema
```python
class NarratorOutput(BaseModel):
    day_number: int
    summary: str           # 2–3 sentences
```

---

## 4. Resolver-fallback — estimate hours/duration

**When:** inside the resolver chain (PRD §9) **only** when OSM/Wikidata/Foursquare lack data.
Low-confidence by design; result is tagged `source: llm_estimate` + flagged to the user.

**Params:** `temperature: 0.2` (grounded), structured output on.

### System prompt
```
You estimate typical opening hours and typical visit duration for a named place, from general
knowledge of places of its type in this city. These are ESTIMATES, not authoritative.

Rules:
- Give per-weekday open/close in 24h local time; use null for days typically closed
  (e.g. many museums close Mondays).
- For places without formal hours (parks, public squares, viewpoints, neighborhoods, 24/7
  venues), return open all day (00:00–23:59) for the relevant days and say so in the caveat.
- If you cannot reasonably estimate, return nulls — do not fabricate precise hours.
- Note any well-known caveat (e.g. "closed Mondays", "seasonal", "last entry 1h before close").

Return ONLY JSON matching the schema.
```

### User message
```
City: {{city}}
Place: {{place_name}}  (category: {{category}})
Estimate typical opening hours per weekday and a typical visit duration.
```

### Output schema
```python
class DayHours(BaseModel):
    open: str | None       # "09:30" or null if closed
    close: str | None

class ResolverEstimate(BaseModel):
    hours: dict[str, DayHours]   # keys: mon..sun
    est_duration_min: int | None
    caveat: str | None
    confidence: Literal["low","medium"]   # never "high" — this is a fallback
```

---

## Prompt versioning

Every prompt carries a **version + hash** recorded in the run manifest (PRD §13.2) so behavior
changes are diffable across runs. Bump the version on any wording change; the hash is computed
from the rendered system prompt.
