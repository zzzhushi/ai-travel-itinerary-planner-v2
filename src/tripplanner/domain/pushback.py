"""Render a feasibility verdict into human-readable pushback suggestions.

Pure string templating — the CLI and web layers show these lines alongside a 409
when a trip is over-committed, has closed-on-all-days places, or conflicting
anchors. See domain/feasibility.py for the verdict these are rendered from.
"""

from __future__ import annotations

from collections.abc import Sequence


def render_suggestions(
    *,
    requested: int,
    fits: int,
    over_by: int,
    closed_all_days: Sequence[str],
    anchor_conflicts: Sequence[str],
) -> tuple[str, ...]:
    """Build one suggestion line per problem: an over-commitment summary, a swap
    offer per closed-on-all-days place, and a pass-through of each anchor conflict.
    Empty when the trip is feasible."""
    suggestions: list[str] = []

    if over_by > 0:
        suggestions.append(
            f"{requested} places requested but only {fits} fit — drop {over_by} or add days."
        )

    for place_id in closed_all_days:
        suggestions.append(f"Swap out '{place_id}': it is closed on all of your travel days.")

    for conflict in anchor_conflicts:
        suggestions.append(f"Anchor conflict: {conflict}")

    return tuple(suggestions)
