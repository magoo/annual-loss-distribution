"""Trusted analytical distributions and random sampling primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from .models import (
    DistributionCurve,
    DistributionType,
    LognormalParams,
    OddsParams,
    ParameterModel,
    ParamsLike,
    ParetoParams,
    PertParams,
)

DEFAULT_CURVE_POINTS = 500
MAX_CURVE_POINTS = 100_000
P95_Z_SCORE = float(stats.norm.ppf(0.95))


@dataclass(frozen=True, slots=True)
class LognormalFit:
    mu: float
    sigma: float


@dataclass(frozen=True, slots=True)
class ParetoFit:
    scale: float
    shape: float


@dataclass(frozen=True, slots=True)
class PertFit:
    alpha: float
    beta: float
    minimum: float
    maximum: float


def coerce_distribution_type(value: DistributionType | str) -> DistributionType:
    """Return a supported distribution enum or raise a useful error."""

    try:
        return DistributionType(value)
    except (TypeError, ValueError) as exc:
        choices = ", ".join(item.value for item in DistributionType)
        raise ValueError(f"unsupported distribution type {value!r}; choose {choices}") from exc


def params_as_mapping(params: ParamsLike | None) -> Mapping[str, Any]:
    """Expose parameter dataclasses and mappings through a common interface."""

    if params is None:
        return {}
    if isinstance(params, Mapping):
        return params
    if isinstance(params, (LognormalParams, ParetoParams)):
        return {"p50": params.p50, "p95": params.p95}
    if isinstance(params, PertParams):
        return {"min": params.min, "mode": params.mode, "max": params.max}
    if isinstance(params, OddsParams):
        return {"odds": params.odds}
    raise TypeError("parameters must be a supported parameter dataclass or mapping")


def coerce_params(
    distribution_type: DistributionType | str,
    params: ParamsLike,
) -> ParameterModel:
    """Normalize a mapping into the parameter model required by a distribution."""

    dist_type = coerce_distribution_type(distribution_type)
    values = params_as_mapping(params)
    if dist_type is DistributionType.LOGNORMAL:
        return LognormalParams(p50=values.get("p50"), p95=values.get("p95"))
    if dist_type is DistributionType.PARETO:
        return ParetoParams(p50=values.get("p50"), p95=values.get("p95"))
    return PertParams.from_dict(values)


def fit_lognormal(params: ParamsLike) -> LognormalFit:
    """Fit lognormal ``mu`` and ``sigma`` exactly from P50 and P95."""

    values = params_as_mapping(params)
    p50 = float(values["p50"])
    p95 = float(values["p95"])
    mu = float(np.log(p50))
    sigma = float((np.log(p95) - mu) / P95_Z_SCORE)
    return LognormalFit(mu=mu, sigma=sigma)


def fit_pareto(params: ParamsLike) -> ParetoFit:
    """Fit Pareto Type I scale and shape exactly from P50 and P95."""

    values = params_as_mapping(params)
    p50 = float(values["p50"])
    p95 = float(values["p95"])
    shape = float(np.log(10.0) / np.log(p95 / p50))
    scale = float(p50 / np.power(2.0, 1.0 / shape))
    return ParetoFit(scale=scale, shape=shape)


def fit_pert(params: ParamsLike) -> PertFit:
    """Derive modified-PERT (scaled beta) shape parameters."""

    values = params_as_mapping(params)
    minimum = float(values.get("min", values.get("minimum")))
    mode = float(values["mode"])
    maximum = float(values.get("max", values.get("maximum")))
    width = maximum - minimum
    alpha = float(1.0 + 4.0 * (mode - minimum) / width)
    beta = float(1.0 + 4.0 * (maximum - mode) / width)
    return PertFit(alpha=alpha, beta=beta, minimum=minimum, maximum=maximum)


def distribution_curve(
    distribution_type: DistributionType | str,
    params: ParamsLike,
    *,
    num_points: int = DEFAULT_CURVE_POINTS,
) -> DistributionCurve:
    """Return plot-ready analytical PDF/CDF arrays for a valid model."""

    if isinstance(num_points, bool) or not isinstance(num_points, (int, np.integer)):
        raise TypeError("num_points must be an integer")
    if not 2 <= num_points <= MAX_CURVE_POINTS:
        raise ValueError(f"num_points must be between 2 and {MAX_CURVE_POINTS:,}")

    dist_type = coerce_distribution_type(distribution_type)
    # Local import keeps validation's workload checks dependent on, rather than
    # cyclic with, the distribution moment functions below.
    from .validation import require_valid_params

    normalized = require_valid_params("cost", dist_type, params)

    if dist_type is DistributionType.LOGNORMAL:
        fit = fit_lognormal(normalized)
        model = stats.lognorm(s=fit.sigma, scale=np.exp(fit.mu))
        lower, upper = model.ppf((0.001, 0.999))
        x = np.geomspace(lower, upper, num_points, dtype=np.float64)
    elif dist_type is DistributionType.PARETO:
        fit = fit_pareto(normalized)
        model = stats.pareto(b=fit.shape, scale=fit.scale)
        lower = fit.scale
        upper = float(model.ppf(0.999))
        x = np.geomspace(lower, upper, num_points, dtype=np.float64)
    else:
        fit = fit_pert(normalized)
        width = fit.maximum - fit.minimum
        model = stats.beta(
            a=fit.alpha,
            b=fit.beta,
            loc=fit.minimum,
            scale=width,
        )
        x = np.linspace(fit.minimum, fit.maximum, num_points, dtype=np.float64)

    pdf = np.asarray(model.pdf(x), dtype=np.float64)
    cdf = np.asarray(model.cdf(x), dtype=np.float64)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(pdf)) and np.all(np.isfinite(cdf))):
        raise FloatingPointError("distribution curve contains non-finite values")
    return DistributionCurve(distribution_type=dist_type, x=x, pdf=pdf, cdf=cdf)


def distribution_mean(
    distribution_type: DistributionType | str,
    params: ParamsLike,
) -> float:
    """Return the theoretical mean (``inf`` for infinite-mean Pareto models)."""

    dist_type = coerce_distribution_type(distribution_type)
    if dist_type is DistributionType.LOGNORMAL:
        fit = fit_lognormal(params)
        return float(np.exp(fit.mu + fit.sigma**2 / 2.0))
    if dist_type is DistributionType.PERT:
        fit = fit_pert(params)
        return float(fit.minimum + (fit.maximum - fit.minimum) * fit.alpha / (fit.alpha + fit.beta))
    fit = fit_pareto(params)
    if fit.shape <= 1.0:
        return float("inf")
    return float(fit.shape * fit.scale / (fit.shape - 1.0))


def frequency_work_rate(
    distribution_type: DistributionType | str,
    params: ParamsLike,
) -> float:
    """Estimate event draws per year for pre-flight workload planning.

    Infinite-mean Pareto models use P95 as a stable planning proxy. The hard
    runtime draw ceiling remains authoritative if a seeded run is unusually
    expensive.
    """

    dist_type = coerce_distribution_type(distribution_type)
    mean = distribution_mean(dist_type, params)
    if np.isfinite(mean):
        return mean
    if dist_type is DistributionType.PARETO:
        return float(params_as_mapping(params)["p95"])
    return float("nan")


def sample_distribution(
    distribution_type: DistributionType | str,
    params: ParamsLike,
    size: int,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Draw non-negative samples with NumPy's explicit ``Generator`` API.

    This is public primarily for testing and advanced composition. Application
    code should normally call one of the bounded simulation entry points.
    """

    if isinstance(size, bool) or not isinstance(size, (int, np.integer)) or size < 0:
        raise ValueError("size must be a non-negative integer")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be an instance of numpy.random.Generator")

    dist_type = coerce_distribution_type(distribution_type)
    from .validation import MAX_TOTAL_EVENT_DRAWS, require_valid_params

    if size > MAX_TOTAL_EVENT_DRAWS:
        raise ValueError(f"size must not exceed {MAX_TOTAL_EVENT_DRAWS:,}")

    normalized = require_valid_params("cost", dist_type, params)
    if dist_type is DistributionType.LOGNORMAL:
        fit = fit_lognormal(normalized)
        samples = rng.lognormal(mean=fit.mu, sigma=fit.sigma, size=size)
    elif dist_type is DistributionType.PERT:
        fit = fit_pert(normalized)
        unit_samples = rng.beta(fit.alpha, fit.beta, size=size)
        samples = fit.minimum + (fit.maximum - fit.minimum) * unit_samples
    else:
        fit = fit_pareto(normalized)
        samples = fit.scale * (rng.pareto(fit.shape, size=size) + 1.0)

    result = np.asarray(samples, dtype=np.float64)
    if not np.all(np.isfinite(result)) or np.any(result < 0):
        raise FloatingPointError("distribution sampling produced an invalid value")
    return result
