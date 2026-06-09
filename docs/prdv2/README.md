# docs/prdv2 — skill-output comparison set

This folder exists to **compare PRD-generation skills** on the same source material (the design
conversation for the AI travel itinerary planner).

| File | Produced by | Notes |
|------|-------------|-------|
| [PRD.md](./PRD.md) | **to-prd** skill (Matt Pocock engineering-PRD style) | The comparison artifact |
| [ROADMAP.md](./ROADMAP.md) | carried over from [docs/](../) | Cross-links repointed to the canonical `docs/` tree |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | carried over from [docs/](../) | Same |

The other half of the comparison is the **prd-builder** output at [docs/PRD.md](../PRD.md).

## How the two PRDs differ

- **prd-builder** ([docs/PRD.md](../PRD.md)) — product-management template: executive summary,
  personas, success-metrics frameworks, functional/non-functional requirement tables, risks,
  a full future-requirements triage, stakeholder-style structure.
- **to-prd** ([PRD.md](./PRD.md)) — engineering template: problem/solution from the user's
  POV, one long user-story list, explicit Implementation & Testing **Decisions** (with the
  testing seams), Out of Scope, Further Notes. Leaner, build-oriented; defaults to publishing
  to an issue tracker (redirected here).

Canonical sources of truth remain in [docs/](../): [CONTEXT.md](../../CONTEXT.md),
[docs/PRD.md](../PRD.md), [docs/ARCHITECTURE.md](../ARCHITECTURE.md),
[docs/ROADMAP.md](../ROADMAP.md), and [ADRs](../adr/). The copies here are for side-by-side
reading only — edit the originals, not these.
