import numpy as np
import pytest

from annual_loss import (
    AnnualLossError,
    ParameterValidationError,
    Section,
    SimulationConfig,
    SimulationSafetyError,
    simulate_annual_loss,
    simulate_scenarios,
)

ANNUAL_PARAMS = {
    "frequency_dist_type": "lognormal",
    "frequency_params": {"p50": 5, "p95": 20},
    "cost_dist_type": "lognormal",
    "cost_params": {"p50": 50_000, "p95": 500_000},
}

ODDS_SCENARIO = {
    "id": 1,
    "name": "Phishing",
    "frequency_method": "odds",
    "frequency_params": {"odds": 2},
    "cost_dist_type": "lognormal",
    "cost_params": {"p50": 10_000, "p95": 50_000},
}

MIXED_COST_SCENARIOS = [
    ODDS_SCENARIO,
    {
        "id": 2,
        "name": "Supply chain",
        "frequency_method": "odds",
        "frequency_params": {"odds": 4},
        "cost_dist_type": "pert",
        "cost_params": {"min": 5_000, "mode": 20_000, "max": 250_000},
    },
]

PAIRED_SCENARIOS = [
    {
        "id": 1,
        "name": "Low cost",
        "frequency_method": "odds",
        "frequency_params": {"odds": 1},
        "cost_dist_type": "pert",
        "cost_params": {"min": 100, "mode": 100.5, "max": 101},
    },
    {
        "id": 2,
        "name": "High cost",
        "frequency_method": "odds",
        "frequency_params": {"odds": 1},
        "cost_dist_type": "pert",
        "cost_params": {"min": 1_000, "mode": 1_000.5, "max": 1_001},
    },
]


def assert_valid_result(result, *, rounds: int, kind: Section) -> None:
    assert result.num_rounds == rounds
    assert result.kind is kind
    assert result.is_histogram is True
    assert result.samples.size > 0
    assert np.all(np.isfinite(result.samples))
    assert np.all(result.samples >= 0)
    assert result.x.size == result.y_cdf.size
    assert np.all(np.diff(result.x) > 0)
    assert np.all(np.diff(result.y_cdf) >= 0)
    assert result.y_cdf[-1] == 1


def test_annual_loss_is_deterministic_and_reports_seed() -> None:
    config = SimulationConfig(seed=2026, rounds=1_000)
    first = simulate_annual_loss(**ANNUAL_PARAMS, config=config)
    second = simulate_annual_loss(**ANNUAL_PARAMS, config=config)

    assert_valid_result(first, rounds=1_000, kind=Section.LOSS)
    assert first.seed == 2026
    assert np.all(np.diff(first.samples) >= 0)
    assert first.samples[-1] == first.x[-1]
    np.testing.assert_array_equal(first.samples, second.samples)
    np.testing.assert_array_equal(first.x, second.x)
    np.testing.assert_array_equal(first.y_cdf, second.y_cdf)


def test_annual_loss_sums_independent_costs_per_incident() -> None:
    result = simulate_annual_loss(
        "pert",
        {"min": 1.49, "mode": 1.5, "max": 1.51},
        "pert",
        {"min": 100, "mode": 100.5, "max": 101},
        config=SimulationConfig(rounds=1_000),
    )

    assert np.any((result.samples >= 100) & (result.samples <= 101))
    assert np.any((result.samples >= 200) & (result.samples <= 202))
    # If a single cost draw were multiplied by frequency, paired incident costs
    # would be exactly equal far more often; continuous independent draws are not.
    two_event_losses = result.samples[result.samples >= 200]
    assert np.unique(two_event_losses).size > 100


def test_annual_loss_preserves_zero_loss_years() -> None:
    result = simulate_annual_loss(
        "lognormal",
        {"p50": 0.25, "p95": 1},
        "lognormal",
        {"p50": 1_000, "p95": 10_000},
        config=SimulationConfig(rounds=2_000),
    )

    zero_probability = np.mean(result.samples == 0)
    assert zero_probability > 0
    assert result.x[0] == 0
    assert result.y_cdf[0] == pytest.approx(zero_probability)


@pytest.mark.parametrize(
    ("frequency_type", "frequency_params", "cost_type", "cost_params"),
    [
        ("lognormal", {"p50": 5, "p95": 20}, "pert", {"min": 1, "mode": 5, "max": 20}),
        ("pert", {"min": 0, "mode": 5, "max": 20}, "lognormal", {"p50": 10, "p95": 100}),
        ("pareto", {"p50": 5, "p95": 20}, "lognormal", {"p50": 10, "p95": 100}),
        ("pert", {"min": 0, "mode": 5, "max": 20}, "pert", {"min": 1, "mode": 5, "max": 20}),
    ],
)
def test_annual_loss_supports_mixed_distributions(
    frequency_type, frequency_params, cost_type, cost_params
) -> None:
    result = simulate_annual_loss(
        frequency_type,
        frequency_params,
        cost_type,
        cost_params,
        config=SimulationConfig(rounds=1_000),
    )

    assert_valid_result(result, rounds=1_000, kind=Section.LOSS)


def test_default_infinite_mean_pareto_frequency_stays_bounded() -> None:
    result = simulate_annual_loss(
        "pareto",
        {"p50": 1, "p95": 10},
        "lognormal",
        {"p50": 1_000, "p95": 10_000},
        config=SimulationConfig(rounds=1_000),
    )

    assert_valid_result(result, rounds=1_000, kind=Section.LOSS)
    assert result.total_event_draws <= 1_500_000


def test_automatic_round_planning_targets_a_bounded_event_workload() -> None:
    result = simulate_annual_loss(
        "pert",
        {"min": 99, "mode": 100, "max": 101},
        "pert",
        {"min": 1, "mode": 2, "max": 3},
    )

    assert result.num_rounds == 7_500
    assert result.total_event_draws == pytest.approx(750_000, rel=0.01)


@pytest.mark.parametrize("rounds", [999, 100_001])
def test_annual_loss_rejects_round_counts_outside_safe_bounds(rounds) -> None:
    with pytest.raises(SimulationSafetyError, match="rounds"):
        simulate_annual_loss(**ANNUAL_PARAMS, config=SimulationConfig(rounds=rounds))


def test_annual_loss_rejects_invalid_and_explosive_models_before_sampling() -> None:
    with pytest.raises(ParameterValidationError):
        simulate_annual_loss(
            "lognormal",
            {"p50": 10, "p95": 10},
            "lognormal",
            {"p50": 1_000, "p95": 10_000},
        )
    with pytest.raises(AnnualLossError):
        simulate_annual_loss(
            "pareto",
            {"p50": 1, "p95": 1e12},
            "lognormal",
            {"p50": 1_000, "p95": 10_000},
        )


def test_scenario_frequency_is_seeded_integer_output() -> None:
    config = SimulationConfig(seed=99, rounds=2_000)
    first = simulate_scenarios([ODDS_SCENARIO], "frequency", config=config)
    second = simulate_scenarios([ODDS_SCENARIO], "frequency", config=config)

    assert_valid_result(first, rounds=2_000, kind=Section.FREQUENCY)
    np.testing.assert_array_equal(first.samples, second.samples)
    assert np.all(first.samples == np.floor(first.samples))
    assert np.mean(first.samples) == pytest.approx(0.5, abs=0.04)
    assert first.total_event_draws == int(np.sum(first.samples))


def test_scenario_loss_is_seeded_and_reproducible() -> None:
    config = SimulationConfig(seed=17, rounds=1_000)
    first = simulate_scenarios(MIXED_COST_SCENARIOS, config=config)
    second = simulate_scenarios(MIXED_COST_SCENARIOS, config=config)

    assert_valid_result(first, rounds=1_000, kind=Section.LOSS)
    assert first.seed == 17
    assert first.samples.size == first.num_rounds
    assert first.total_event_draws > 0
    np.testing.assert_array_equal(first.samples, second.samples)
    np.testing.assert_array_equal(first.x, second.x)
    np.testing.assert_array_equal(first.y_cdf, second.y_cdf)


def test_each_scenario_frequency_uses_its_paired_cost_model() -> None:
    result = simulate_scenarios(PAIRED_SCENARIOS, config=SimulationConfig(rounds=1_000))

    assert_valid_result(result, rounds=1_000, kind=Section.LOSS)
    assert result.total_event_draws == 2_000
    assert np.all((result.samples >= 1_100) & (result.samples <= 1_102))


def test_scenario_cost_output_contains_each_rows_incident_costs() -> None:
    result = simulate_scenarios(
        PAIRED_SCENARIOS,
        Section.COST,
        config=SimulationConfig(seed=42, rounds=1_000),
    )

    assert_valid_result(result, rounds=1_000, kind=Section.COST)
    assert result.total_event_draws == 2_000
    assert result.samples.size == result.total_event_draws
    assert np.all((result.samples[:1_000] >= 100) & (result.samples[:1_000] <= 101))
    assert np.all((result.samples[1_000:] >= 1_000) & (result.samples[1_000:] <= 1_001))


def test_scenario_frequency_ignores_invalid_costs_when_not_needed() -> None:
    frequency_only = {
        **ODDS_SCENARIO,
        "cost_dist_type": "unsupported",
        "cost_params": {"p50": 10_000, "p95": 1_000},
    }
    result = simulate_scenarios(
        [frequency_only],
        "frequency",
        config=SimulationConfig(rounds=1_000),
    )

    assert_valid_result(result, rounds=1_000, kind=Section.FREQUENCY)


@pytest.mark.parametrize("section", [Section.COST, Section.LOSS])
def test_cost_and_loss_validate_every_scenario_cost(section) -> None:
    invalid_second_cost = [
        ODDS_SCENARIO,
        {
            **MIXED_COST_SCENARIOS[1],
            "cost_params": {"min": 5_000, "mode": 20_000, "max": 10_000},
        },
    ]

    with pytest.raises(ParameterValidationError, match="max"):
        simulate_scenarios(invalid_second_cost, section)


@pytest.mark.parametrize("section", [Section.COST, Section.LOSS])
def test_cost_and_loss_reject_unsupported_scenario_cost_types(section) -> None:
    invalid_second_type = [
        ODDS_SCENARIO,
        {**MIXED_COST_SCENARIOS[1], "cost_dist_type": "unsupported"},
    ]

    with pytest.raises(ValueError, match="unsupported distribution type"):
        simulate_scenarios(invalid_second_type, section)


def test_scenario_simulation_rejects_empty_or_invalid_models() -> None:
    with pytest.raises(AnnualLossError, match="at least one"):
        simulate_scenarios([], "loss")

    invalid = {**ODDS_SCENARIO, "frequency_params": {"odds": 0}}
    with pytest.raises(ParameterValidationError):
        simulate_scenarios([invalid], "loss")

    unknown_method = {**ODDS_SCENARIO, "frequency_method": "unsupported"}
    with pytest.raises(ValueError, match="unsupported frequency method"):
        simulate_scenarios([unknown_method], "loss")


@pytest.mark.parametrize("section", [None, "", "hybrid", object()])
def test_scenario_simulation_rejects_invalid_sections(section) -> None:
    with pytest.raises(ValueError, match="unsupported section"):
        simulate_scenarios([ODDS_SCENARIO], section)


@pytest.mark.parametrize(
    "scenarios",
    [None, "scenario", b"scenario", ODDS_SCENARIO, [42]],
)
def test_scenario_simulation_rejects_invalid_inputs(scenarios) -> None:
    with pytest.raises(TypeError, match="scenario"):
        simulate_scenarios(scenarios)


def test_removed_hybrid_arguments_are_not_accepted() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        simulate_scenarios([ODDS_SCENARIO], frequency_scenario_mode=True)


def test_scenario_aggregate_workload_is_bounded_before_sampling() -> None:
    high_frequency_rows = [
        {
            **ODDS_SCENARIO,
            "id": index,
            "frequency_method": "pert",
            "frequency_params": {"min": 799, "mode": 800, "max": 801},
        }
        for index in (1, 2)
    ]

    with pytest.raises(SimulationSafetyError, match="maximum event-draw workload"):
        simulate_scenarios(high_frequency_rows, "loss")


@pytest.mark.parametrize("rounds", [999, 10_001])
def test_scenario_rounds_stay_within_safe_bounds(rounds) -> None:
    with pytest.raises(SimulationSafetyError, match="rounds"):
        simulate_scenarios([ODDS_SCENARIO], "frequency", config=SimulationConfig(rounds=rounds))
