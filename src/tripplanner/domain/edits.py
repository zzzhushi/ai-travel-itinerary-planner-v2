"""Deterministic trip edits for the re-solve loop."""

from __future__ import annotations

from dataclasses import replace

from tripplanner.domain.models import RankedPlace, Trip


def with_swap(trip: Trip, *, remove_id: str, add: RankedPlace) -> Trip:
    """Return a new Trip with the place whose id == remove_id removed from
    `places`, and `add` appended. If remove_id is not present, just append add."""
    places = (*(rp for rp in trip.places if rp.place.id != remove_id), add)
    return replace(trip, places=places)


def with_rating(
    trip: Trip, *, place_id: str, rating: int, duration_override_min: int | None = None
) -> Trip:
    """Return a new Trip where the RankedPlace whose place.id == place_id has its
    `rating` replaced (and `duration_override_min` replaced only when the argument
    is not None; otherwise keep the existing override). Other places unchanged."""

    def _update(rp: RankedPlace) -> RankedPlace:
        if rp.place.id != place_id:
            return rp
        if duration_override_min is not None:
            return replace(rp, rating=rating, duration_override_min=duration_override_min)
        return replace(rp, rating=rating)

    places = tuple(_update(rp) for rp in trip.places)
    return replace(trip, places=places)
