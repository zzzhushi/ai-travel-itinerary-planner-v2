"""Pure formatting helpers: domain objects → display strings"""

from __future__ import annotations

from tripplanner.domain.models import Day, Itinerary, RankedPlace


def _fmt(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _day_block(day: Day) -> list[str]:
    """The body lines for one day: travel legs, stops, and the total — no header."""
    stops = day.stops
    if not stops:
        return ["  (no stops scheduled)", "Total travel: 0 min"]

    lines: list[str] = []
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
        f"  ({day.return_travel_min} min travel, return)"
    )

    lines.append(f"Total travel: {day.total_travel_min()} min")
    return lines


def _unscheduled_line(unscheduled: tuple[RankedPlace, ...]) -> str:
    names = ", ".join(rp.place.name for rp in unscheduled)
    return f"\n⚠ Did not fit ({len(unscheduled)}): {names}"


def format_itinerary(itin: Itinerary) -> str:
    """Human-readable itinerary: a numbered, dated block per day, then any
    unscheduled places. Works for single- and multi-day trips."""
    lines: list[str] = []
    for n, day in enumerate(itin.days, start=1):
        lines.append(f"Day {n} — {day.date.isoformat()}")
        lines.extend(_day_block(day))
    if itin.unscheduled:
        lines.append(_unscheduled_line(itin.unscheduled))
    return "\n".join(lines)
