# LLMProvider abstraction with a multi-provider fallback chain

The LLM is not hardcoded to Gemini. All model access goes through an **`LLMProvider`**
interface (`gather_options()`, `schedule()`), with a configurable **fallback chain** that
mirrors the geo tiering of ADR-0001:

1. **Gemini** — used for the grounded `gather` step (real, current places).
2. **Groq / OpenRouter free tier** — used for token-heavy `schedule` + re-prompts.
3. **Local Ollama** — unlimited, offline last resort; never runs out of quota.

A provider that returns a quota/rate-limit error causes the chain to fall back to the
next provider, so free-tier exhaustion degrades gracefully instead of stopping the app.

## Grounding is decoupled from the model

Real-time web grounding is a **Gemini-specific capability**; Groq and Ollama lack it. So:

- The grounded `gather` step prefers Gemini (it is low-volume and `(city, interest)`-cached,
  so it rarely hits limits), **or**
- An optional pluggable **`SearchProvider`** (e.g. Tavily/Brave free tier, local SearXNG)
  supplies real places to *any* model, so even local Ollama can gather grounded Options.

When neither grounding path is available, Options fall back to the model's training
knowledge, and geocoding (ADR-0001) remains the reality check.

## Considered Options

- *Single free hosted provider (e.g. Groq only)* — rejected: still one quota ceiling and no
  grounding.
- *Local-only Ollama* — viable and fully offline, but quality is hardware-bound and loses
  grounding; kept as the chain's last tier rather than the only option.

## Consequences

- Core prompts and parsing must be **model-agnostic**: no Gemini-only assumptions on the
  hot path, and structured-output handling must tolerate varying JSON conformance across
  models (defensive parse + repair retry, already planned).
- Token burn during development is further reduced by the `(city, interest)` gather cache,
  which should land early.
- The `LLMProvider` interface is the swap point for both fallback and future model upgrades.
