# Design principles — concrete constraints for mockups

These are bans and systems, not vibes. A mockup violating them gets fixed before the user ever sees it.

## Systems (pick once per direction, then never deviate within it)

- **Type scale:** one ratio (e.g. 1.25), max 4 sizes on a screen. One typeface family, two weights. System font stacks or one webfont — never two webfonts.
- **Spacing:** 8px grid (4px allowed for tight internal padding). Every margin/padding is a grid multiple. Inconsistent spacing is the #1 tell of generated UI.
- **Color:** one accent color, used only for primary actions and key highlights. Neutrals carry everything else (5–6 steps of one gray ramp). Semantic colors (error/success) used semantically only.
- **Radius and elevation:** one radius value, one shadow style, applied consistently.

## Bans (the slop list)

- Gradients as decoration (gradient buttons, gradient hero backgrounds, purple-to-blue anything).
- Emoji as icons. Use a consistent icon set or none.
- Lorem ipsum, "John Doe", placeholder gray boxes — every mockup uses real copy from the PRD scenarios.
- Three different button styles on one screen. Primary, secondary, text — that's the budget.
- Centered-everything layouts; default to left-aligned text with intentional alignment.
- "Dashboard cards with big numbers" unless the PRD actually has metrics worth glancing at.

## Positive heuristics

- Density should match the task: planning a trip is information-dense work — favor scannable structure (timelines, grouped lists) over airy marketing-page layouts.
- The screen should answer the user's current question first; visual hierarchy = order of likely questions.
- Empty states, loading states, and error states are part of the design — sketch at least the most important one per screen.
- When in doubt, remove. The difference between generated UI and designed UI is mostly what's NOT there.

## Self-critique checklist (run on the screenshot before showing the user)

1. Could you mistake this for any other AI-generated app? What single element makes it specifically THIS product?
2. Squint test: is the hierarchy still readable blurred?
3. Count accent-color uses — more than ~3 per screen means the accent is decoration, not signal.
4. Is every spacing value on the grid?
5. Does the copy sound like the product, or like a template?
