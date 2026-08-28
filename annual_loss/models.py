"""Typed models shared by the annual-loss numerical engine.

The dataclasses deliberately do not reject invalid values at construction time.
That keeps them useful for reactive form state: callers can construct a model,
pass it to :func:`annual_loss.validate_params`, and show field-level errors.
Simulation entry points always validate before doing any work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeAlias

import numpy as np


class DistributionType(StrEnum):
    """Supported continuous probability distributions."""

    LOGNORMAL = "lognormal"
    PERT = "pert"
    PARETO = "pareto"


class FrequencyMethod(StrEnum):
    """Frequency choices available to an individual scenario."""

    ODDS = "odds"
    LOGNORMAL = "lognormal"
    PERT = "pert"
    PARETO = "pareto"


class Section(StrEnum):
    """A modeled section of the application."""

    FREQUENCY = "frequency"
    COST = "cost"
    LOSS = "loss"


@dataclass(frozen=True, slots=True)
class LognormalParams:
    """A lognormal distribution specified by its median and P95."""

    p50: float
    p95: float


@dataclass(frozen=True, slots=True)
class ParetoParams:
    """A Pareto Type I distribution specified by its median and P95."""

    p50: float
    p95: float


@dataclass(frozen=True, slots=True)
class PertParams:
    """A modified-PERT distribution on ``[minimum, maximum]``.

    ``min`` and ``max`` match the field names used by the original web
    application and by Marimo's editable tables; ``minimum`` and ``maximum``
    read-only aliases are available for descriptive Python code.
    """

    min: float
    mode: float
    max: float

    @property
    def minimum(self) -> float:
        return self.min

    @property
    def maximum(self) -> float:
        return self.max

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> PertParams:
        return cls(
            min=values.get("min", values.get("minimum")),
            mode=values.get("mode"),
            max=values.get("max", values.get("maximum")),
        )


@dataclass(frozen=True, slots=True)
class OddsParams:
    """A Bernoulli annual frequency expressed as one occurrence in N years."""

    odds: float


ParameterModel: TypeAlias = LognormalParams | ParetoParams | PertParams | OddsParams
ParamsLike: TypeAlias = ParameterModel | Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Scenario:
    """A named threat scenario with independent frequency and cost models."""

    name: str
    frequency_method: FrequencyMethod | str
    frequency_params: ParamsLike
    cost_dist_type: DistributionType | str
    cost_params: ParamsLike
    id: int | str | None = None

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> Scenario:
        """Create a scenario from a Marimo row or source-app style mapping.

        Nested ``frequency_params``/``cost_params`` mappings, camelCase source
        keys, and flat ``frequency_p50``/``cost_p50`` table columns are all
        accepted. Unknown columns are ignored.
        """

        frequency_method = row.get(
            "frequency_method", row.get("frequencyMethod", FrequencyMethod.ODDS)
        )
        cost_dist_type = row.get(
            "cost_dist_type",
            row.get(
                "cost_distribution",
                row.get("costDistType", DistributionType.LOGNORMAL),
            ),
        )

        frequency_params = row.get("frequency_params", row.get("frequencyParams"))
        if frequency_params is None:
            frequency_params = _prefixed_params(row, "frequency")

        cost_params = row.get("cost_params", row.get("costParams"))
        if cost_params is None:
            cost_params = _prefixed_params(row, "cost")

        return cls(
            id=row.get("id"),
            name=str(row.get("name", "Scenario")),
            frequency_method=frequency_method,
            frequency_params=frequency_params,
            cost_dist_type=cost_dist_type,
            cost_params=cost_params,
        )


def _prefixed_params(row: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("odds", "p50", "p95", "min", "mode", "max"):
        snake_key = f"{prefix}_{key}"
        if snake_key in row:
            result[key] = row[snake_key]
    return result


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Optional reproducibility and round-count controls.

    A ``None`` seed selects the stable default for the chosen simulation
    engine (12,345 for distribution mode and 54,321 for scenario mode). A
    ``None`` round count lets the engine choose a safe workload from the
    modeled frequency.
    """

    seed: int | None = None
    rounds: int | None = None

    def __post_init__(self) -> None:
        if self.seed is not None and (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, (int, np.integer))
            or self.seed < 0
        ):
            raise ValueError("seed must be a non-negative integer or None")
        if self.rounds is not None and (
            isinstance(self.rounds, bool) or not isinstance(self.rounds, (int, np.integer))
        ):
            raise ValueError("rounds must be an integer or None")


@dataclass(frozen=True, slots=True)
class DistributionCurve:
    """Plot-ready analytical PDF and CDF arrays."""

    distribution_type: DistributionType
    x: np.ndarray
    pdf: np.ndarray
    cdf: np.ndarray

    @property
    def y_pdf(self) -> np.ndarray:
        return self.pdf

    @property
    def y_cdf(self) -> np.ndarray:
        return self.cdf


@dataclass(frozen=True, slots=True)
class EmpiricalCDF:
    """A compact empirical CDF suitable for plotting heavy-tailed results."""

    x: np.ndarray
    probabilities: np.ndarray

    @property
    def y_cdf(self) -> np.ndarray:
        return self.probabilities

    def percentile(self, probability: float) -> float:
        # Local import avoids a models <-> statistics import cycle.
        from .statistics import interpolate_percentile

        return interpolate_percentile(self.x, self.probabilities, probability)


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """A reproducible Monte Carlo result and its compact empirical CDF."""

    samples: np.ndarray
    cdf: EmpiricalCDF
    num_rounds: int
    seed: int
    total_event_draws: int
    kind: Section = Section.LOSS

    @property
    def x(self) -> np.ndarray:
        return self.cdf.x

    @property
    def y_cdf(self) -> np.ndarray:
        return self.cdf.probabilities

    @property
    def is_histogram(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """A central confidence interval and median."""

    level: float
    lower_percentile: float
    median_percentile: float
    upper_percentile: float
    lower: float
    median: float
    upper: float


@dataclass(frozen=True, slots=True)
class PanelStatistic:
    """Descriptive statistics for one elicited panel parameter."""

    average: float | None
    minimum: float | None
    maximum: float | None
    stddev: float | None
    count: int

    # Source-app compatible names make table rendering straightforward.
    @property
    def avg(self) -> float | None:
        return self.average

    @property
    def min(self) -> float | None:
        return self.minimum

    @property
    def max(self) -> float | None:
        return self.maximum


DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "Product Exploit", "odds", {"odds": 3}, "lognormal", {"p50": 100_000, "p95": 1_000_000}, 1
    ),
    Scenario(
        "Malicious Insider",
        "odds",
        {"odds": 10},
        "lognormal",
        {"p50": 200_000, "p95": 2_000_000},
        2,
    ),
    Scenario("DDoS", "odds", {"odds": 2}, "lognormal", {"p50": 20_000, "p95": 200_000}, 3),
    Scenario(
        "Supply Chain", "odds", {"odds": 20}, "lognormal", {"p50": 200_000, "p95": 2_000_000}, 4
    ),
    Scenario(
        "Credential Leak / Theft",
        "odds",
        {"odds": 2},
        "lognormal",
        {"p50": 30_000, "p95": 300_000},
        5,
    ),
    Scenario(
        "Compromised Software Download",
        "odds",
        {"odds": 15},
        "lognormal",
        {"p50": 50_000, "p95": 500_000},
        6,
    ),
    Scenario(
        "Social Engineering", "odds", {"odds": 3}, "lognormal", {"p50": 25_000, "p95": 250_000}, 7
    ),
    Scenario(
        "Zero Day Targeting Employee",
        "odds",
        {"odds": 50},
        "lognormal",
        {"p50": 100_000, "p95": 1_000_000},
        8,
    ),
    Scenario(
        "Exposed and Exploited Service",
        "odds",
        {"odds": 5},
        "lognormal",
        {"p50": 50_000, "p95": 500_000},
        9,
    ),
    Scenario(
        "Ransomware", "odds", {"odds": 5}, "lognormal", {"p50": 100_000, "p95": 1_000_000}, 10
    ),
)
