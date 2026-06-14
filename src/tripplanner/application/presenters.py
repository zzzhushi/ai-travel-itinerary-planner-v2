"""Pure formatting helpers: domain objects → display strings."""

from __future__ import annotations

from tripplanner.domain.models import Itinerary


def _fmt(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def format_day(itin: Itinerary) -> str:
    """Human-readable single-day itinerary. Returns a string; caller prints."""
    lines: list[str] = [f"Day {itin.day.date.isoformat()}"]

    stops = itin.day.stops
    if not stops:
        lines.append("  (no stops scheduled)")
        lines.append("Total travel: 0 min")
        if itin.unscheduled:
            names = ", ".join(rp.place.name for rp in itin.unscheduled)
            lines.append(f"\n⚠ Did not fit ({len(itin.unscheduled)}): {names}")
        return "\n".join(lines)

    # First travel leg: lodging → first stop
    first = stops[0]
    depart_lodging = _fmt(first.arrive_min - first.travel_from_prev_min)
    lines.append(
        f"  {depart_lodging}  Lodging → {first.place.name}"
        f"  ({first.travel_from_prev_min} min travel)"
    )

    for i, stop in enumerate(stops):
        arrive = _fmt(stop.arrive_min)
        depart = _fmt(stop.depart_min)
        lines.append(f"  {arrive}  {stop.place.name:<30} arrive {arrive}  depart {depart}")

        if i < len(stops) - 1:
            nxt = stops[i + 1]
            lines.append(
                f"  {_fmt(stop.depart_min)}  {stop.place.name} → {nxt.place.name}"
                f"  ({nxt.travel_from_prev_min} min travel)"
            )

    # Return leg
    last = stops[-1]
    lines.append(
        f"  {_fmt(last.depart_min)}  {last.place.name} → Lodging"
        f"  ({itin.day.return_travel_min} min travel, return)"
    )

    lines.append(f"Total travel: {itin.day.total_travel_min()} min")

    if itin.unscheduled:
        names = ", ".join(rp.place.name for rp in itin.unscheduled)
        lines.append(f"\n⚠ Did not fit ({len(itin.unscheduled)}): {names}")

    return "\n".join(lines)
