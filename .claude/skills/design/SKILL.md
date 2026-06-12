---
name: design
description: Produce UI/UX direction after PRD approval — HTML mockups the user picks from, then a design-system doc. Use when starting visual design ("mockups", "what should it look like", "design the UI") for a product with a user interface.
---

# Design: Mockups and Design System

You are producing **agreement artifacts** — mockups exist so the user and later milestones agree on what the product looks like before feature code exists. They are not production code and will not be reused as code.

## Step 0: acquire taste before generating (mandatory)

Ask the user for **2–3 reference products or screenshots whose look they'd steal**, and what specifically they like about each (density? typography? calm?). Taste transfer beats taste generation — generated-from-nothing UI converges on generic slop. If the user has no references, WebSearch screenshots of the 3 best-regarded products in the category and ask the user to react to them. Do not generate a single mockup before this step.

## Step 1: divergent directions

Read the PRD (`docs/prd.md`) core flows. Build **2–3 distinct visual directions** as self-contained HTML files (inline CSS, no build step) in `docs/design/mockups/direction-<n>.html`, each covering the same one or two core screens so they're comparable. Rules from `references/design-principles.md` apply to every direction. Use **real product copy** drawn from the PRD's scenarios — a travel app mockup shows an actual Lisbon itinerary, never lorem ipsum or placeholder boxes.

## Step 2: iterate visually, never blind

Render each mockup (browser preview) and **screenshot it**. Self-critique the screenshot against the principles doc *before* showing the user — fix violations first. Then present screenshots to the user, take their reactions, and iterate on the chosen direction. Never iterate by editing HTML you haven't rendered; slop survives in unrendered markup.

## Step 3: extract the design system

When the user approves a direction, distill it into `docs/design/design-system.md` using `references/design-doc-template.md`: palette, type scale, spacing, core components, voice. This doc — not the mockup HTML — is what milestones and implementation reference. Keep approved mockups in place as the visual ground truth; delete rejected directions.

## Gate

User explicitly approves: one direction, its screenshot set, and the design-system doc. Milestones must not begin UI work before this approval exists.
