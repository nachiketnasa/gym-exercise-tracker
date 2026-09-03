"""Personal-record calculation (issue #11).

Pure Python, no database: :func:`calculate_prs` takes an exercise category and
an iterable of :class:`PRInput` rows (one per logged exercise entry) and returns
one PR record per metric tracked for that category. Computed on read - there is
no PR table.

PR metrics, by category. Each PR name is a prefix plus a stem from the shared
vocabulary in ``app.metrics`` (``weight``/``reps``/``estimated_1rm`` /
``pace``/``distance``/``duration``), so PRs, goals (#12) and progress (#13)
stay aligned:

* strength: ``max_weight``, ``max_reps``, ``max_estimated_1rm``
* cardio:   ``best_pace`` (smallest / fastest), ``longest_distance``,
  ``longest_duration``

``estimated_1rm`` uses the Epley formula ``weight * (1 + reps / 30)`` (see
``app.metrics.epley_1rm``). Tie-break when two entries share the best value:
the earlier session ``date`` wins, and if the dates are equal the smaller
``entry_id`` wins. Entries missing the field a metric needs are skipped for
that metric only; a metric with no qualifying entry yields ``value=None`` and
null ``achieved_on``/``session_id``/``entry_id``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.metrics import metric_is_minimised, metric_value


@dataclass(frozen=True)
class PRInput:
    """One logged exercise entry, flattened with its session date."""

    entry_id: int
    session_id: int
    session_date: date
    weight: float | None = None
    reps: int | None = None
    distance_meters: float | None = None
    duration_seconds: float | None = None
    pace_seconds_per_km: float | None = None


@dataclass(frozen=True)
class PRRecord:
    metric: str
    value: float | None
    achieved_on: date | None
    session_id: int | None
    entry_id: int | None


#: PR metric name -> stem in the shared vocabulary, by exercise category.
PR_METRICS_BY_CATEGORY: dict[str, dict[str, str]] = {
    "strength": {
        "max_weight": "weight",
        "max_reps": "reps",
        "max_estimated_1rm": "estimated_1rm",
    },
    "cardio": {
        "best_pace": "pace",
        "longest_distance": "distance",
        "longest_duration": "duration",
    },
}


def pr_metric_names(category: str) -> list[str]:
    """The PR metric names for ``category`` (empty for an unknown category)."""
    return list(PR_METRICS_BY_CATEGORY.get(category, {}))


def calculate_prs(category: str, entries: Iterable[PRInput]) -> list[PRRecord]:
    """Return one :class:`PRRecord` per metric tracked for ``category``."""
    rows = list(entries)
    records: list[PRRecord] = []

    for name, stem in PR_METRICS_BY_CATEGORY.get(category, {}).items():
        minimise = metric_is_minimised(stem)
        best: PRInput | None = None
        best_value: float | None = None

        for entry in rows:
            value = metric_value(entry, stem)
            if value is None:
                continue
            if best is None:
                best, best_value = entry, value
                continue
            beats = value < best_value if minimise else value > best_value
            ties = value == best_value and (
                (entry.session_date, entry.entry_id)
                < (best.session_date, best.entry_id)
            )
            if beats or ties:
                best, best_value = entry, value

        if best is None:
            records.append(PRRecord(name, None, None, None, None))
        else:
            records.append(
                PRRecord(
                    metric=name,
                    value=best_value,
                    achieved_on=best.session_date,
                    session_id=best.session_id,
                    entry_id=best.entry_id,
                )
            )

    return records
