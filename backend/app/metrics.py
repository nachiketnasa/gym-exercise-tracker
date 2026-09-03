"""Single source of truth for the metric vocabulary.

Shared verbatim by PR auto-calculation (#11), the Goals API (#12) and the
per-exercise progress API (#13) so the three features never drift apart.

The vocabulary, keyed by exercise category:

* ``strength`` -> ``weight``, ``reps``, ``estimated_1rm``
* ``cardio``   -> ``pace``, ``distance``, ``duration``

#11 exposes these as prefixed PR names (``max_weight``, ``best_pace`` ...); the
*stems* are exactly the identifiers below.
"""

from __future__ import annotations

STRENGTH_METRICS: tuple[str, ...] = ("weight", "reps", "estimated_1rm")
CARDIO_METRICS: tuple[str, ...] = ("pace", "distance", "duration")

METRICS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "strength": STRENGTH_METRICS,
    "cardio": CARDIO_METRICS,
}

#: Every valid metric identifier, regardless of category.
ALL_METRICS: frozenset[str] = frozenset(STRENGTH_METRICS + CARDIO_METRICS)


def metrics_for_category(category: str) -> tuple[str, ...]:
    """Return the metrics valid for ``category`` (empty tuple if unknown)."""
    return METRICS_BY_CATEGORY.get(category, ())


def is_valid_metric(category: str, metric: str) -> bool:
    """True when ``metric`` is in the vocabulary for ``category``."""
    return metric in metrics_for_category(category)


def epley_1rm(weight: float, reps: float) -> float:
    """Estimated one-rep-max via the Epley formula: ``weight * (1 + reps / 30)``.

    Shared by #11 (the ``estimated_1rm`` PR) and #13 (the ``estimated_1rm``
    progress series) so both compute the estimate identically.
    """
    return weight * (1 + reps / 30)


def _as_float(value) -> float | None:
    return None if value is None else float(value)


def metric_value(entry, metric: str) -> float | None:
    """Pull one metric's value from an entry-like object.

    ``entry`` is any object carrying the exercise-entry attribute names
    (``weight``, ``reps``, ``distance_meters``, ``duration_seconds``,
    ``pace_seconds_per_km``). Returns ``None`` when the entry is missing a
    field the metric needs (``estimated_1rm`` needs both a weight and a
    non-zero rep count), so that entry is skipped for this metric only.

    Shared by #11 (PRs) and #13 (progress) so both read entries identically.
    """
    if metric == "weight":
        return _as_float(entry.weight)
    if metric == "reps":
        return _as_float(entry.reps)
    if metric == "estimated_1rm":
        if entry.weight is None or not entry.reps:
            return None
        return epley_1rm(float(entry.weight), float(entry.reps))
    if metric == "distance":
        return _as_float(entry.distance_meters)
    if metric == "duration":
        return _as_float(entry.duration_seconds)
    if metric == "pace":
        return _as_float(entry.pace_seconds_per_km)
    raise KeyError(metric)


def metric_is_minimised(metric: str) -> bool:
    """True for metrics where "better" means smaller (only ``pace``)."""
    return metric == "pace"
