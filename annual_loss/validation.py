"""Field-level model validation and simulation safety pre-flight checks."""

from __future__ import annotations

from numbers import Real
from typing import Any

import numpy as np

from .distributions import (
    coerce_distribution_type,
    coerce_params,
    frequency_work_rate,
    params_as_mapping,
)
from .exceptions import ParameterValidationError
from .models import (
    DistributionType,
    FrequencyMethod,
    OddsParams,
    ParameterModel,
    ParamsLike,
    Section,
)

MIN_SIMULATION_ROUNDS = 1_000
MAX_DISTRIBUTION_ROUNDS = 100_000
MAX_SCENARIO_ROUNDS = 10_000
MAX_EVENTS_PER_ROUND = 100_000
TARGET_EVENT_DRAWS = 750_000
MAX_TOTAL_EVENT_DRAWS = 1_500_000


def coerce_section(value: Section | str) -> Section:
    try:
        return Section(value)
    except (TypeError, ValueError) as exc:
        choices = ", ".join(section.value for section in Section)
        raise ValueError(f"unsupported section {value!r}; choose {choices}") from exc


def validate_params(
    section: Section | str,
    distribution_type: DistributionType | FrequencyMethod | str,
    params: ParamsLike | None,
) -> dict[str, str]:
    """Return source-compatible field errors for one parameter set.

    Frequency validation also rejects models that cannot fit inside the hard
    event-work limits. Cost validation is domain-only because costs do not
    determine the number of random draws.
    """

    try:
        section_value = coerce_section(section)
    except ValueError as exc:
        return {"section": str(exc)}
    if section_value is Section.LOSS:
        return {}

    if str(distribution_type) in {"odds", "FrequencyMethod.ODDS"}:
        if section_value is not Section.FREQUENCY:
            return {"distribution": "Odds is only valid for frequency"}
        return _validate_odds(params)

    try:
        dist_type = coerce_distribution_type(distribution_type)
    except ValueError as exc:
        return {"distribution": str(exc)}

    try:
        values = params_as_mapping(params)
    except TypeError as exc:
        return {"parameters": str(exc)}

    if dist_type is DistributionType.PERT:
        errors = _validate_pert(values)
    else:
        errors = _validate_quantiles(values)

    if section_value is not Section.FREQUENCY or errors:
        return errors

    try:
        normalized = coerce_params(dist_type, values)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            work_rate = frequency_work_rate(dist_type, normalized)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        work_rate = float("nan")

    high_key = "max" if dist_type is DistributionType.PERT else "p95"
    high_estimate = float(values[high_key])
    if (
        not np.isfinite(work_rate)
        or work_rate * MIN_SIMULATION_ROUNDS > MAX_TOTAL_EVENT_DRAWS
        or high_estimate > MAX_EVENTS_PER_ROUND
    ):
        errors[high_key] = "Too large to simulate safely"
    return errors


def require_valid_params(
    section: Section | str,
    distribution_type: DistributionType | FrequencyMethod | str,
    params: ParamsLike | None,
) -> ParameterModel:
    """Return normalized parameters, raising on any validation error."""

    errors = validate_params(section, distribution_type, params)
    if errors:
        raise ParameterValidationError(errors)
    if str(distribution_type) in {"odds", "FrequencyMethod.ODDS"}:
        return OddsParams(odds=float(params_as_mapping(params)["odds"]))
    return coerce_params(coerce_distribution_type(distribution_type), params)


def _validate_quantiles(values: dict[str, Any] | Any) -> dict[str, str]:
    errors: dict[str, str] = {}
    p50 = values.get("p50")
    p95 = values.get("p95")
    _validate_number(errors, "p50", p50, positive=True)
    _validate_number(errors, "p95", p95, positive=True)
    if not errors and float(p95) <= float(p50):
        errors["p95"] = "P95 must be greater than P50"
    return errors


def _validate_pert(values: dict[str, Any] | Any) -> dict[str, str]:
    errors: dict[str, str] = {}
    minimum = values.get("min", values.get("minimum"))
    mode = values.get("mode")
    maximum = values.get("max", values.get("maximum"))
    _validate_number(errors, "min", minimum, nonnegative=True)
    _validate_number(errors, "mode", mode, nonnegative=True)
    _validate_number(errors, "max", maximum, positive=True)

    if "min" not in errors and "mode" not in errors and float(mode) <= float(minimum):
        errors["mode"] = "Must be greater than minimum"
    if "mode" not in errors and "max" not in errors and float(maximum) <= float(mode):
        errors["max"] = "Must be greater than most likely"
    return errors


def _validate_odds(params: ParamsLike | None) -> dict[str, str]:
    try:
        values = params_as_mapping(params)
    except TypeError as exc:
        return {"parameters": str(exc)}
    errors: dict[str, str] = {}
    odds = values.get("odds")
    _validate_number(errors, "odds", odds)
    if "odds" not in errors and float(odds) < 1:
        errors["odds"] = 'Must be at least 1 (means "1 in N years")'
    return errors


def _validate_number(
    errors: dict[str, str],
    field: str,
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> None:
    if value is None or isinstance(value, Real) and not isinstance(value, bool) and np.isnan(value):
        errors[field] = "Required"
        return
    if isinstance(value, bool) or not isinstance(value, Real):
        errors[field] = "Must be a number"
        return
    if not np.isfinite(value):
        errors[field] = "Must be a finite number"
        return
    if positive and value <= 0:
        errors[field] = "Must be greater than 0"
    elif nonnegative and value < 0:
        errors[field] = "Must be 0 or greater"
