"""Per-day time windows, including partial first/last days (M2 task 2)."""

from __future__ import annotations

from tripplanner.domain.models import MultiDayTrip


def day_windows(trip: MultiDayTrip) -> list[tuple[int, int]]:
    """(start_min, end_min) for each of trip.num_days days. Day 1 starts at the
    arrival time; the last day ends at the departure time; middle days use the
    standard [day_start_min, day_end_min] window. A single-day trip uses the
    arrival→departure window."""
    if trip.num_days == 1:
        return [(trip.arrival_min, trip.departure_min)]

    windows = [(trip.arrival_min, trip.day_end_min)]  # partial first day
    windows.extend((trip.day_start_min, trip.day_end_min) for _ in range(trip.num_days - 2))
    windows.append((trip.day_start_min, trip.departure_min))  # partial last day
    return windows
