# Design system doc template

```markdown
# Design System: <product>
Approved: <date> · Source mockup: docs/design/mockups/direction-<n>.html

## Palette
- Accent: #... (primary actions, active states only)
- Neutrals: #... / #... / #... / #... (text, secondary text, borders, surfaces)
- Semantic: error #..., success #..., warning #...

## Typography
- Family: <stack>
- Scale: <sizes with usage — e.g. 24/20/16/13: page title / section / body / caption>
- Weights: <e.g. 600 headings, 400 body>

## Spacing & shape
- Grid: 8px (4px internal)
- Radius: <value> · Shadow: <single definition>

## Core components
For each (button, input, card, list row, nav...): one-line description +
states that exist (default/hover/disabled/error). Reference the mockup for visuals.

## Layout
Page structure, breakpoints if responsive, max content width.

## Voice
How the product talks (labels, empty states, errors). 2–3 example strings.

## Non-negotiables
The 3–5 rules implementation must never break (from design-principles.md +
direction-specific ones).
```

Keep it under ~2 pages — it gets loaded into implementation context for every UI task; verbosity here taxes every milestone.
