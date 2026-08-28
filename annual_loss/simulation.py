"""Bounded Monte Carlo engines for annual loss and threat scenarios."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .distributions import (
    coerce_distribution_type,
    frequency_work_rate,
    sample_distribution,
)
from .exceptions import AnnualLossError, ParameterValidationError, SimulationSafetyError
from .models import (
    DistributionType,
    FrequencyMethod,
    ParamsLike,
    Scenario,
    Section,
    SimulationConfig,
    SimulationResult,
)
from .statistics import empirical_cdf
from .validation import (
    MAX_DISTRIBUTION_ROUNDS,
    MAX_EVENTS_PER_ROUND,
    MAX_SCENARIO_ROUNDS,
    MAX_TOTAL_EVENT_DRAWS,
    MIN_SIMULATION_ROUNDS,
    TARGET_EVENT_DRAWS,
    coerce_section,
    require_valid_params,
)

DEFAULT_ANNUAL_SEED = 12_345
DEFAULT_SCENARIO_SEED = 54_321


def simulate_annual_loss(
    frequency_dist_type: DistributionType | str,
    frequency_params: ParamsLike,
    cost_dist_type: DistributionType | str,
    cost_params: ParamsLike,
    *,
    config: SimulationConfig | None = None,
) -> SimulationResult:
    """Simulate yearly losses by summing an independent cost per incident.

    Frequency samples are rounded to annual incident counts using the source
    application's non-negative ``Math.round`` semantics. The round count is
    automatically reduced for expensive frequency models, while never falling
    below 1,000 or exceeding 100,000.
    """

    frequency_type = coerce_distribution_type(frequency_dist_type)
    cost_type = coerce_distribution_type(cost_dist_type)
    normalized_frequency = require_valid_params(Section.FREQUENCY, frequency_type, frequency_params)
    normalized_cost = require_valid_params(Section.COST, cost_type, cost_params)

    work_rate = frequency_work_rate(frequency_type, normalized_frequency)
    resolved_config = config or SimulationConfig()
    rounds, seed = _resolve_workload(
        resolved_config,
        default_seed=DEFAULT_ANNUAL_SEED,
        maximum_rounds=MAX_DISTRIBUTION_ROUNDS,
        work_rate=work_rate,
        adjust_to_target=True,
    )
    rng = np.random.default_rng(seed)

    raw_frequency = sample_distribution(frequency_type, normalized_frequency, rounds, rng)
    event_counts = _round_event_counts(raw_frequency)
    total_events = _check_total_event_draws(event_counts)
    costs = sample_distribution(cost_type, normalized_cost, total_events, rng)
    annual_losses = _sum_costs_by_year(costs, event_counts)
    # Preserve the source engine's annual-loss contract: samples are returned
    # sorted, while scenario-section samples retain their simulation order.
    annual_losses.sort()

    return _simulation_result(
        samples=annual_losses,
        rounds=rounds,
        seed=seed,
        total_events=total_events,
        kind=Section.LOSS,
    )


def simulate_scenarios(
    scenarios: Sequence[Scenario | Mapping[str, Any]] | Iterable[Scenario | Mapping[str, Any]],
    section: Section | str = Section.LOSS,
    *,
    frequency_scenario_mode: bool = True,
    cost_scenario_mode: bool = True,
    frequency_dist_type: DistributionType | str = DistributionType.LOGNORMAL,
    frequency_params: ParamsLike | None = None,
    cost_dist_type: DistributionType | str = DistributionType.LOGNORMAL,
    cost_params: ParamsLike | None = None,
    config: SimulationConfig | None = None,
) -> SimulationResult:
    """Run scenario-only or hybrid frequency/cost simulation.

    When frequency is distribution-based but costs are scenario-based, each
    incident selects a scenario uniformly, preserving the source behavior.
    When scenario frequencies are active, each incident retains its scenario's
    cost distribution.
    """

    section_value = coerce_section(section)
    scenario_list = _coerce_scenarios(scenarios)
    if not scenario_list:
        raise AnnualLossError("at least one scenario is required")
    if not isinstance(frequency_scenario_mode, bool) or not isinstance(cost_scenario_mode, bool):
        raise TypeError("scenario mode flags must be booleans")

    need_cost = section_value is not Section.FREQUENCY
    normalized_frequency: ParamsLike | None = None
    normalized_cost: ParamsLike | None = None
    frequency_type: DistributionType | None = None
    cost_type: DistributionType | None = None

    scenario_frequency_methods: list[FrequencyMethod] = []
    scenario_frequency_params: list[ParamsLike] = []
    if frequency_scenario_mode:
        work_rate = 0.0
        for scenario in scenario_list:
            method = _coerce_frequency_method(scenario.frequency_method)
            normalized = require_valid_params(Section.FREQUENCY, method, scenario.frequency_params)
            scenario_frequency_methods.append(method)
            scenario_frequency_params.append(normalized)
            if method is FrequencyMethod.ODDS:
                work_rate += 1.0 / float(normalized.odds)
            else:
                work_rate += frequency_work_rate(DistributionType(method.value), normalized)
    else:
        if frequency_params is None:
            raise ParameterValidationError({"frequency_params": "Required"})
        frequency_type = coerce_distribution_type(frequency_dist_type)
        normalized_frequency = require_valid_params(
            Section.FREQUENCY, frequency_type, frequency_params
        )
        work_rate = frequency_work_rate(frequency_type, normalized_frequency)

    scenario_cost_types: list[DistributionType] = []
    scenario_cost_params: list[ParamsLike] = []
    if need_cost and cost_scenario_mode:
        for scenario in scenario_list:
            scenario_cost_type = coerce_distribution_type(scenario.cost_dist_type)
            scenario_cost_param = require_valid_params(
                Section.COST, scenario_cost_type, scenario.cost_params
            )
            scenario_cost_types.append(scenario_cost_type)
            scenario_cost_params.append(scenario_cost_param)
    elif need_cost:
        if cost_params is None:
            raise ParameterValidationError({"cost_params": "Required"})
        cost_type = coerce_distribution_type(cost_dist_type)
        normalized_cost = require_valid_params(Section.COST, cost_type, cost_params)

    resolved_config = config or SimulationConfig()
    rounds, seed = _resolve_workload(
        resolved_config,
        default_seed=DEFAULT_SCENARIO_SEED,
        maximum_rounds=MAX_SCENARIO_ROUNDS,
        work_rate=work_rate,
        adjust_to_target=need_cost,
    )
    rng = np.random.default_rng(seed)

    if frequency_scenario_mode:
        counts_by_scenario = []
        for method, params in zip(
            scenario_frequency_methods, scenario_frequency_params, strict=True
        ):
            if method is FrequencyMethod.ODDS:
                probability = 1.0 / float(params.odds)
                counts = (rng.random(rounds) < probability).astype(np.int64)
            else:
                raw = sample_distribution(DistributionType(method.value), params, rounds, rng)
                counts = _round_event_counts(raw)
            counts_by_scenario.append(counts)
        total_counts = np.sum(np.stack(counts_by_scenario), axis=0, dtype=np.int64)
        _check_per_round_counts(total_counts)
    else:
        assert frequency_type is not None and normalized_frequency is not None
        raw = sample_distribution(frequency_type, normalized_frequency, rounds, rng)
        total_counts = _round_event_counts(raw)
        counts_by_scenario = []

    total_events = int(np.sum(total_counts, dtype=np.int64))
    if need_cost and total_events > MAX_TOTAL_EVENT_DRAWS:
        raise SimulationSafetyError(
            f"seeded run requires {total_events:,} event draws; limit is {MAX_TOTAL_EVENT_DRAWS:,}"
        )

    if section_value is Section.FREQUENCY:
        return _simulation_result(
            samples=total_counts.astype(np.float64),
            rounds=rounds,
            seed=seed,
            total_events=total_events,
            kind=section_value,
        )

    annual_losses = np.zeros(rounds, dtype=np.float64)
    cost_chunks: list[NDArray[np.float64]] = []

    if frequency_scenario_mode and cost_scenario_mode:
        for counts, scenario_cost_type, scenario_cost_param in zip(
            counts_by_scenario,
            scenario_cost_types,
            scenario_cost_params,
            strict=True,
        ):
            scenario_events = int(np.sum(counts, dtype=np.int64))
            costs = sample_distribution(
                scenario_cost_type, scenario_cost_param, scenario_events, rng
            )
            cost_chunks.append(costs)
            annual_losses += _sum_costs_by_year(costs, counts)
    elif frequency_scenario_mode:
        assert cost_type is not None and normalized_cost is not None
        costs = sample_distribution(cost_type, normalized_cost, total_events, rng)
        cost_chunks.append(costs)
        annual_losses = _sum_costs_by_year(costs, total_counts)
    elif cost_scenario_mode:
        costs = np.empty(total_events, dtype=np.float64)
        scenario_choices = rng.integers(0, len(scenario_list), size=total_events, dtype=np.int64)
        for index, (scenario_cost_type, scenario_cost_param) in enumerate(
            zip(scenario_cost_types, scenario_cost_params, strict=True)
        ):
            selected = np.flatnonzero(scenario_choices == index)
            costs[selected] = sample_distribution(
                scenario_cost_type, scenario_cost_param, selected.size, rng
            )
        cost_chunks.append(costs)
        annual_losses = _sum_costs_by_year(costs, total_counts)
    else:
        assert cost_type is not None and normalized_cost is not None
        costs = sample_distribution(cost_type, normalized_cost, total_events, rng)
        cost_chunks.append(costs)
        annual_losses = _sum_costs_by_year(costs, total_counts)

    if not np.all(np.isfinite(annual_losses)):
        raise FloatingPointError("annual loss aggregation produced a non-finite value")

    if section_value is Section.COST:
        if total_events == 0:
            raise AnnualLossError("simulation produced no incident costs")
        output_samples = np.concatenate(cost_chunks)
    else:
        output_samples = annual_losses

    return _simulation_result(
        samples=output_samples,
        rounds=rounds,
        seed=seed,
        total_events=total_events,
        kind=section_value,
    )


def simulate_hybrid(*args: Any, **kwargs: Any) -> SimulationResult:
    """Alias with an explicit name for scenario/distribution hybrid runs."""

    return simulate_scenarios(*args, **kwargs)


def _coerce_scenarios(
    scenarios: Sequence[Scenario | Mapping[str, Any]] | Iterable[Scenario | Mapping[str, Any]],
) -> list[Scenario]:
    if scenarios is None or isinstance(scenarios, (str, bytes, Mapping)):
        raise TypeError("scenarios must be an iterable of Scenario objects or row mappings")
    result: list[Scenario] = []
    for scenario in scenarios:
        if isinstance(scenario, Scenario):
            result.append(scenario)
        elif isinstance(scenario, Mapping):
            result.append(Scenario.from_dict(scenario))
        else:
            raise TypeError("each scenario must be a Scenario or row mapping")
    return result


def _coerce_frequency_method(value: FrequencyMethod | DistributionType | str) -> FrequencyMethod:
    try:
        return FrequencyMethod(value)
    except (TypeError, ValueError) as exc:
        choices = ", ".join(method.value for method in FrequencyMethod)
        raise ValueError(f"unsupported frequency method {value!r}; choose {choices}") from exc


def _resolve_workload(
    config: SimulationConfig,
    *,
    default_seed: int,
    maximum_rounds: int,
    work_rate: float,
    adjust_to_target: bool,
) -> tuple[int, int]:
    if not np.isfinite(work_rate) or work_rate < 0:
        raise SimulationSafetyError("frequency model does not have a safe work estimate")

    if config.rounds is not None:
        rounds = int(config.rounds)
        if not MIN_SIMULATION_ROUNDS <= rounds <= maximum_rounds:
            raise SimulationSafetyError(
                f"rounds must be between {MIN_SIMULATION_ROUNDS:,} and {maximum_rounds:,}"
            )
    elif adjust_to_target:
        rounds = min(
            maximum_rounds,
            max(
                MIN_SIMULATION_ROUNDS,
                int(np.floor(TARGET_EVENT_DRAWS / max(1.0, work_rate))),
            ),
        )
    else:
        rounds = maximum_rounds

    if adjust_to_target and rounds * work_rate > MAX_TOTAL_EVENT_DRAWS:
        raise SimulationSafetyError("frequency model exceeds the maximum event-draw workload")
    seed = default_seed if config.seed is None else int(config.seed)
    return rounds, seed


def _round_event_counts(samples: NDArray[np.float64]) -> NDArray[np.int64]:
    if not np.all(np.isfinite(samples)) or np.any(samples < 0):
        raise FloatingPointError("frequency sampling produced an invalid value")
    rounded = np.floor(samples + 0.5)
    if np.any(rounded > MAX_EVENTS_PER_ROUND):
        raise SimulationSafetyError(f"a simulated year exceeds {MAX_EVENTS_PER_ROUND:,} incidents")
    return rounded.astype(np.int64)


def _check_per_round_counts(counts: NDArray[np.int64]) -> None:
    if np.any(counts < 0) or np.any(counts > MAX_EVENTS_PER_ROUND):
        raise SimulationSafetyError(
            f"aggregate scenario frequency exceeds {MAX_EVENTS_PER_ROUND:,} incidents in a year"
        )


def _check_total_event_draws(counts: NDArray[np.int64]) -> int:
    _check_per_round_counts(counts)
    total = int(np.sum(counts, dtype=np.int64))
    if total > MAX_TOTAL_EVENT_DRAWS:
        raise SimulationSafetyError(
            f"seeded run requires {total:,} event draws; limit is {MAX_TOTAL_EVENT_DRAWS:,}"
        )
    return total


def _sum_costs_by_year(
    costs: NDArray[np.float64],
    event_counts: NDArray[np.int64],
) -> NDArray[np.float64]:
    total_events = int(np.sum(event_counts, dtype=np.int64))
    if costs.size != total_events:
        raise RuntimeError("cost sample count does not match the simulated incidents")
    if total_events == 0:
        return np.zeros(event_counts.size, dtype=np.float64)
    years = np.repeat(np.arange(event_counts.size, dtype=np.int64), event_counts)
    totals = np.bincount(years, weights=costs, minlength=event_counts.size)
    if not np.all(np.isfinite(totals)):
        raise FloatingPointError("annual loss aggregation produced a non-finite value")
    return np.asarray(totals, dtype=np.float64)


def _simulation_result(
    *,
    samples: NDArray[np.float64],
    rounds: int,
    seed: int,
    total_events: int,
    kind: Section,
) -> SimulationResult:
    output = np.asarray(samples, dtype=np.float64)
    if output.size == 0:
        raise AnnualLossError("simulation produced no output samples")
    return SimulationResult(
        samples=output,
        cdf=empirical_cdf(output),
        num_rounds=rounds,
        seed=seed,
        total_event_draws=total_events,
        kind=kind,
    )
