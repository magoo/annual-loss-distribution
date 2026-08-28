"""Empirical distribution, confidence, and elicitation-panel statistics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from numbers import Real
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from .distributions import params_as_mapping
from .models import (
    ConfidenceInterval,
    EmpiricalCDF,
    LognormalParams,
    OddsParams,
    PanelStatistic,
    ParetoParams,
    PertParams,
    SimulationResult,
)

DEFAULT_EMPIRICAL_POINTS = 500
MAX_EMPIRICAL_POINTS = 100_000


def empirical_cdf(
    samples: ArrayLike,
    *,
    num_points: int = DEFAULT_EMPIRICAL_POINTS,
    assume_sorted: bool = False,
) -> EmpiricalCDF:
    """Build a compact empirical CDF without hiding zero mass or extremes.

    Positive outcomes use a log-spaced grid focused on the central 99.8% so a
    Pareto tail remains readable. The actual maximum is appended separately,
    and zero-loss years are retained as an explicit probability mass.
    """

    if isinstance(num_points, bool) or not isinstance(num_points, (int, np.integer)):
        raise TypeError("num_points must be an integer")
    if not 2 <= num_points <= MAX_EMPIRICAL_POINTS:
        raise ValueError(f"num_points must be between 2 and {MAX_EMPIRICAL_POINTS:,}")

    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("samples must be a one-dimensional array")
    if values.size == 0:
        raise ValueError("samples must not be empty")
    if not np.all(np.isfinite(values)):
        raise ValueError("samples must contain only finite values")
    if np.any(values < 0):
        raise ValueError("samples must be non-negative")

    if assume_sorted:
        if np.any(values[1:] < values[:-1]):
            raise ValueError("samples were declared sorted but are not non-decreasing")
        sorted_values = values
    else:
        sorted_values = np.sort(values)

    first = float(sorted_values[0])
    last = float(sorted_values[-1])
    if last <= first:
        return EmpiricalCDF(
            x=np.asarray([first], dtype=np.float64),
            probabilities=np.asarray([1.0], dtype=np.float64),
        )

    first_positive_index = int(np.searchsorted(sorted_values, 0.0, side="right"))
    x_values: list[float] = []
    if first_positive_index > 0:
        x_values.append(0.0)

    positive_count = sorted_values.size - first_positive_index
    if positive_count > 0:
        lower_index = first_positive_index + int(np.floor(positive_count * 0.001))
        upper_index = first_positive_index + min(
            int(np.floor(positive_count * 0.999)), positive_count - 1
        )
        lower = float(sorted_values[lower_index])
        upper = float(sorted_values[upper_index])
        if lower > 0 and upper > lower:
            grid_points = max(2, num_points - len(x_values) - 1)
            x_values.extend(np.geomspace(lower, upper, grid_points).tolist())
        else:
            x_values.append(lower)

    if not x_values or last > x_values[-1]:
        x_values.append(last)

    # Degenerate quantized inputs can create duplicate adjacent grid endpoints.
    x = np.unique(np.asarray(x_values, dtype=np.float64))
    probabilities = (
        np.searchsorted(sorted_values, x, side="right").astype(np.float64) / sorted_values.size
    )
    return EmpiricalCDF(x=x, probabilities=probabilities)


def interpolate_percentile(
    x: ArrayLike,
    probabilities: ArrayLike,
    probability: float,
) -> float:
    """Linearly interpolate an x-value from monotone CDF arrays."""

    x_values = np.asarray(x, dtype=np.float64)
    cdf_values = np.asarray(probabilities, dtype=np.float64)
    if x_values.ndim != 1 or cdf_values.ndim != 1 or x_values.size != cdf_values.size:
        raise ValueError("x and probabilities must be equal-length one-dimensional arrays")
    if x_values.size == 0:
        raise ValueError("CDF arrays must not be empty")
    if not isinstance(probability, Real) or isinstance(probability, bool):
        raise TypeError("probability must be a number")
    if not np.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if not np.all(np.isfinite(x_values)) or not np.all(np.isfinite(cdf_values)):
        raise ValueError("CDF arrays must contain only finite values")
    if np.any(x_values[1:] < x_values[:-1]) or np.any(cdf_values[1:] < cdf_values[:-1]):
        raise ValueError("CDF arrays must be non-decreasing")

    if probability <= cdf_values[0]:
        return float(x_values[0])
    if probability >= cdf_values[-1]:
        return float(x_values[-1])

    upper_index = int(np.searchsorted(cdf_values, probability, side="left"))
    lower_index = upper_index - 1
    lower_p = cdf_values[lower_index]
    upper_p = cdf_values[upper_index]
    if upper_p == lower_p:
        return float(x_values[upper_index])
    fraction = (probability - lower_p) / (upper_p - lower_p)
    return float(x_values[lower_index] + fraction * (x_values[upper_index] - x_values[lower_index]))


def confidence_interval(
    data: SimulationResult | EmpiricalCDF | ArrayLike,
    level: float = 0.90,
) -> ConfidenceInterval:
    """Compute a central confidence interval plus the median.

    ``level`` is expressed as a fraction; the app's supported UI range is
    0.50 through 0.95 inclusive.
    """

    if not isinstance(level, Real) or isinstance(level, bool):
        raise TypeError("level must be a number")
    if not np.isfinite(level) or not 0.50 <= level <= 0.95:
        raise ValueError("level must be between 0.50 and 0.95")

    cdf = data.cdf if isinstance(data, SimulationResult) else data
    if not isinstance(cdf, EmpiricalCDF):
        cdf = empirical_cdf(cdf)

    lower_percentile = (1.0 - float(level)) / 2.0
    upper_percentile = 1.0 - lower_percentile
    return ConfidenceInterval(
        level=float(level),
        lower_percentile=lower_percentile,
        median_percentile=0.5,
        upper_percentile=upper_percentile,
        lower=cdf.percentile(lower_percentile),
        median=cdf.percentile(0.5),
        upper=cdf.percentile(upper_percentile),
    )


def panel_analytics(
    rows: Any,
    *,
    fields: Sequence[str] | None = None,
) -> dict[str, PanelStatistic]:
    """Compute averages, ranges, and sample standard deviations by field.

    Rows may be parameter dataclasses, plain parameter mappings, source-style
    ``{"params": {...}}`` panelists, or a dataframe-like object supporting
    ``to_dict(orient="records")``.
    """

    normalized_rows = _normalize_panel_rows(rows)
    selected_fields = list(fields) if fields is not None else _discover_fields(normalized_rows)
    analytics: dict[str, PanelStatistic] = {}
    for field in selected_fields:
        values: list[float] = []
        for row in normalized_rows:
            value = row.get(field)
            if (
                value is None
                or isinstance(value, Real)
                and not isinstance(value, bool)
                and np.isnan(value)
            ):
                continue
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"panel field {field!r} must contain numbers")
            if not np.isfinite(value):
                raise ValueError(f"panel field {field!r} must contain finite values")
            values.append(float(value))

        if not values:
            analytics[field] = PanelStatistic(None, None, None, None, 0)
            continue
        array = np.asarray(values, dtype=np.float64)
        analytics[field] = PanelStatistic(
            average=float(np.mean(array)),
            minimum=float(np.min(array)),
            maximum=float(np.max(array)),
            stddev=float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
            count=int(array.size),
        )
    return analytics


def average_panel_params(
    rows: Any,
    *,
    fields: Sequence[str] | None = None,
) -> dict[str, float | None]:
    """Return the per-field means used as effective panel parameters."""

    return {
        field: statistic.average
        for field, statistic in panel_analytics(rows, fields=fields).items()
    }


def _normalize_panel_rows(rows: Any) -> list[Mapping[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict") and not isinstance(rows, Mapping):
        try:
            rows = rows.to_dict(orient="records")
        except TypeError:
            rows = rows.to_dict("records")
    if isinstance(rows, (LognormalParams, ParetoParams, PertParams, OddsParams)):
        rows = [rows]
    elif isinstance(rows, Mapping):
        rows = [rows]
    elif not isinstance(rows, Iterable) or isinstance(rows, (str, bytes)):
        raise TypeError("rows must be an iterable of panel parameter rows")

    normalized: list[Mapping[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            params = row.get("params", row)
        elif hasattr(row, "params"):
            params = row.params
        else:
            params = row
        mapping = params_as_mapping(params)
        normalized.append(mapping)
    return normalized


def _discover_fields(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    fields: list[str] = []
    ignored = {"id", "name"}
    for row in rows:
        for key in row:
            if key not in ignored and key not in fields:
                fields.append(key)
    return fields
