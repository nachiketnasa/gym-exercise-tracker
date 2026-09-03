"""Per-exercise progress series (issue #13).

Pure Python, no database: :func:`progress_series` takes a metric stem and an
iterable of :class:`ProgressInput` rows and returns a chartable, date-ascending
list of ``{date, value}`` points - at most one point per date.

That date's ``value`` is the best for the metric: the maximum for ``weight``,
``reps``, ``estimated_1rm``, ``distance`` and ``duration``, and the minimum for
``pace`` (see ``app.metrics.metric_is_minimised``). ``estimated_1rm`` uses the
Epley formula, identical to #11. Entries missing the field the metric needs
produce no point.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.metrics import metric_is_minimised, metric_value


@dataclass(frozen=True)
class ProgressInput:
    """One logged exercise entry, flattened with its session date."""

    session_date: date
    weight: float | None = None
    reps: int | None = None
    distance_meters: float | None = None
    duration_seconds: float | None = None
    pace_seconds_per_km: float | None = None


@dataclass(frozen=True)
class ProgressPoint:
    date: date
    value: float


def progress_series(
    metric: str, entries: Iterable[ProgressInput]
) -> list[ProgressPoint]:
    """Return date-ascending ``{date, value}`` points, one per date."""
    minimise = metric_is_minimised(metric)
    pick = min if minimise else max

    best_by_date: dict[date, float] = {}
    for entry in entries:
        value = metric_value(entry, metric)
        if value is None:
            continue
        if entry.session_date in best_by_date:
            best_by_date[entry.session_date] = pick(
                best_by_date[entry.session_date], value
            )
        else:
            best_by_date[entry.session_date] = value

    return [
        ProgressPoint(date=day, value=best_by_date[day])
        for day in sorted(best_by_date)
    ]
