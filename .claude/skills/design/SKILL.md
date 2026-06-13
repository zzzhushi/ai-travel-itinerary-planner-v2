---
name: design
description: Produce UI/UX direction after PRD approval — HTML mockups the user picks from, then a design-system doc. Use when starting visual design ("mockups", "what should it look like", "design the UI") for a product with a user interface.
---

# Design: Mockups and Design System

You are producing **agreement artifacts** — they exist so the user and later milestones agree on what the product looks/feels like before feature code exists. They are not production code and will not be reused as code.

## Mode (from the PRD's project type)

- **product** → HTML mockups, steps 0–3 below.
- **infra/library** → the agreement artifact is **example client code written before implementation** in `docs/design/usage-examples/` (the 2–3 most important call paths, written as a consumer would want them), plus a one-page API sketch. The iteration loop is "does this usage code feel right to write?" — if the example is awkward, the API is wrong and you just learned it for free. Steps 0–3 don't apply; user approval of the examples + sketch is the gate.
- **data/automation** → usually no design stage; say so and skip unless the PRD shows a real human-facing surface.

## Step 0: acquire taste before generating (mandatory)

Ask the user for **2–3 reference products or screenshots whose look they'd steal**, and what specifically they like about each (density? typography? calm?). Taste transfer beats taste generation — generated-from-nothing UI converges on generic slop. If the user has no references, WebSearch screenshots of the 3 best-regarded products in the category and ask the user to react to them. Do not generate a single mockup before this step.

## Step 1: divergent directions

Read the PRD (`docs/prd.md`) core flows. Build **2–3 distinct visual directions** as self-contained HTML files (inline CSS, no build step) in `docs/design/mockups/direction-<n>.html`, each covering the same one or two core screens so they're comparable. Rules from `references/design-principles.md` apply to every direction. Use **real product copy** drawn from the PRD's scenarios — actual entity names and realistic data the product would genuinely display, never lorem ipsum, "John Doe", or placeholder boxes.

## Step 2: iterate visually, never blind

Render each mockup (browser preview) and **screenshot it**. Self-critique the screenshot against the principles doc *before* showing the user — fix violations first. Then present screenshots to the user, take their reactions, and iterate on the chosen direction. Never iterate by editing HTML you haven't rendered; slop survives in unrendered markup.

## Step 3: extract the design system

When the user approves a direction, distill it into `docs/design/design-system.md` using `references/design-doc-template.md`: palette, type scale, spacing, core components, voice. This doc — not the mockup HTML — is what milestones and implementation reference. Keep approved mockups in place as the visual ground truth; delete rejected directions.

## Gate

User explicitly approves: one direction, its screenshot set, and the design-system doc. Milestones must not begin UI work before this approval exists.
