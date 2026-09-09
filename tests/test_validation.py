import math

import pytest

from annual_loss import (
    DistributionType,
    FrequencyMethod,
    ParameterValidationError,
    PertParams,
    Scenario,
    SimulationConfig,
    require_valid_params,
    validate_params,
)


@pytest.mark.parametrize("dist_type", ["lognormal", DistributionType.PARETO])
def test_quantile_validation_accepts_valid_input(dist_type) -> None:
    assert validate_params("cost", dist_type, {"p50": 1, "p95": 10}) == {}


@pytest.mark.parametrize(
    ("params", "field", "message"),
    [
        ({"p95": 10}, "p50", "Required"),
        ({"p50": 1}, "p95", "Required"),
        ({"p50": math.nan, "p95": 10}, "p50", "Required"),
        ({"p50": math.inf, "p95": 10}, "p50", "Must be a finite number"),
        ({"p50": 0, "p95": 10}, "p50", "Must be greater than 0"),
        ({"p50": 10, "p95": 10}, "p95", "P95 must be greater than P50"),
    ],
)
def test_quantile_validation_returns_field_errors(params, field, message) -> None:
    assert validate_params("cost", "lognormal", params)[field] == message


def test_pert_validation_accepts_dataclass_and_enforces_ordering() -> None:
    assert validate_params("cost", "pert", PertParams(min=0, mode=2, max=10)) == {}
    assert validate_params("cost", "pert", {"min": -1, "mode": 2, "max": 10}) == {
        "min": "Must be 0 or greater"
    }
    assert validate_params("cost", "pert", {"min": 1, "mode": 1, "max": 10}) == {
        "mode": "Must be greater than minimum"
    }
    assert validate_params("cost", "pert", {"min": 1, "mode": 5, "max": 5}) == {
        "max": "Must be greater than most likely"
    }


@pytest.mark.parametrize("odds", [1, 2.5, 100])
def test_odds_validation_accepts_one_in_n_year_values(odds) -> None:
    assert validate_params("frequency", FrequencyMethod.ODDS, {"odds": odds}) == {}


@pytest.mark.parametrize("odds", [0, 0.5, -1])
def test_odds_validation_rejects_probabilities_above_one(odds) -> None:
    errors = validate_params("frequency", "odds", {"odds": odds})
    assert "at least 1" in errors["odds"]


def test_odds_are_not_a_cost_distribution() -> None:
    assert "distribution" in validate_params("cost", "odds", {"odds": 2})


@pytest.mark.parametrize(
    ("dist_type", "params", "error_field"),
    [
        ("lognormal", {"p50": 1, "p95": 100_001}, "p95"),
        ("pert", {"min": 0, "mode": 1, "max": 100_001}, "max"),
        ("pareto", {"p50": 1, "p95": 1_000_000}, "p95"),
    ],
)
def test_frequency_validation_rejects_unsafe_workloads(dist_type, params, error_field) -> None:
    errors = validate_params("frequency", dist_type, params)
    assert errors[error_field] == "Too large to simulate safely"


def test_cost_validation_does_not_apply_frequency_work_limits() -> None:
    assert validate_params("cost", "lognormal", {"p50": 1, "p95": 100_001}) == {}


def test_require_valid_params_normalizes_mappings() -> None:
    normalized = require_valid_params("cost", "pert", {"min": 0, "mode": 2, "max": 10})

    assert normalized == PertParams(min=0, mode=2, max=10)


def test_require_valid_params_raises_with_field_errors() -> None:
    with pytest.raises(ParameterValidationError) as error:
        require_valid_params("cost", "lognormal", {"p50": 10, "p95": 5})

    assert error.value.errors == {"p95": "P95 must be greater than P50"}


def test_simulation_config_validates_seed_and_round_types() -> None:
    assert SimulationConfig(seed=0, rounds=1_000).seed == 0
    with pytest.raises(ValueError, match="seed"):
        SimulationConfig(seed=-1)
    with pytest.raises(ValueError, match="rounds"):
        SimulationConfig(rounds=1.5)


def test_scenario_from_dict_accepts_source_and_flat_marimo_rows() -> None:
    source = Scenario.from_dict(
        {
            "id": 7,
            "name": "Source row",
            "frequencyMethod": "odds",
            "frequencyParams": {"odds": 3},
            "costDistType": "lognormal",
            "costParams": {"p50": 10, "p95": 100},
        }
    )
    flat = Scenario.from_dict(
        {
            "name": "Flat row",
            "frequency_method": "pert",
            "frequency_min": 0,
            "frequency_mode": 1,
            "frequency_max": 5,
            "cost_distribution": "pareto",
            "cost_p50": 100,
            "cost_p95": 1_000,
        }
    )

    assert source.frequency_params == {"odds": 3}
    assert source.cost_params == {"p50": 10, "p95": 100}
    assert flat.frequency_params == {"min": 0, "mode": 1, "max": 5}
    assert flat.cost_params == {"p50": 100, "p95": 1_000}
