"""Per-day time windows, including partial first/last days."""

from __future__ import annotations

from tripplanner.domain.models import Trip


def day_windows(trip: Trip) -> list[tuple[int, int]]:
    """(start_min, end_min) for each of trip.num_days days. Single-day trips use
    the normal day window. For multi-day trips, day 1 starts at arrival_min (or
    day_start_min when not set), the last day ends at departure_min (or
    day_end_min when not set), and middle days use the full window."""
    if trip.num_days == 1:
        return [(trip.day_start_min, trip.day_end_min)]

    arrival = trip.arrival_min if trip.arrival_min is not None else trip.day_start_min
    departure = trip.departure_min if trip.departure_min is not None else trip.day_end_min

    windows = [(arrival, trip.day_end_min)]  # partial first day
    windows.extend((trip.day_start_min, trip.day_end_min) for _ in range(trip.num_days - 2))
    windows.append((trip.day_start_min, departure))  # partial last day
    return windows
