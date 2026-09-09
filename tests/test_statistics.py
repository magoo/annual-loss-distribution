import numpy as np
import pytest

from annual_loss import (
    EmpiricalCDF,
    LognormalParams,
    average_panel_params,
    confidence_interval,
    empirical_cdf,
    interpolate_percentile,
    panel_analytics,
)


def test_empirical_cdf_preserves_zero_mass_and_full_maximum() -> None:
    result = empirical_cdf([0, 0, 10, 20, 100], num_points=20)

    assert result.x[0] == 0
    assert result.probabilities[0] == pytest.approx(0.4)
    assert result.x[-1] == 100
    assert result.probabilities[-1] == 1
    assert np.all(np.diff(result.x) > 0)
    assert np.all(np.diff(result.probabilities) >= 0)


def test_empirical_cdf_handles_constant_samples() -> None:
    result = empirical_cdf(np.full(20, 7.0))

    np.testing.assert_array_equal(result.x, [7.0])
    np.testing.assert_array_equal(result.y_cdf, [1.0])


def test_empirical_cdf_accepts_verified_sorted_input() -> None:
    result = empirical_cdf([0, 1, 2, 3], assume_sorted=True)

    assert result.x[-1] == 3
    with pytest.raises(ValueError, match="declared sorted"):
        empirical_cdf([0, 2, 1], assume_sorted=True)


@pytest.mark.parametrize("samples", [[], [1, np.nan], [-1, 0, 1], [[1, 2]]])
def test_empirical_cdf_rejects_invalid_samples(samples) -> None:
    with pytest.raises(ValueError):
        empirical_cdf(samples)


def test_percentile_interpolation_matches_source_linear_behavior() -> None:
    x = [0, 10, 20]
    probabilities = [0.2, 0.6, 1.0]

    assert interpolate_percentile(x, probabilities, 0.1) == 0
    assert interpolate_percentile(x, probabilities, 0.4) == pytest.approx(5)
    assert interpolate_percentile(x, probabilities, 0.8) == pytest.approx(15)
    assert interpolate_percentile(x, probabilities, 1.0) == 20


def test_empirical_cdf_percentile_convenience_method() -> None:
    cdf = EmpiricalCDF(np.array([0.0, 10.0]), np.array([0.25, 1.0]))

    assert cdf.percentile(0.25) == 0
    assert cdf.percentile(1.0) == 10


def test_confidence_interval_uses_central_probability_mass() -> None:
    cdf = EmpiricalCDF(
        x=np.array([0.0, 25.0, 50.0, 75.0, 100.0]),
        probabilities=np.array([0.0, 0.25, 0.50, 0.75, 1.0]),
    )
    interval = confidence_interval(cdf, 0.90)

    assert interval.lower_percentile == pytest.approx(0.05)
    assert interval.upper_percentile == pytest.approx(0.95)
    assert interval.lower == pytest.approx(5)
    assert interval.median == pytest.approx(50)
    assert interval.upper == pytest.approx(95)


@pytest.mark.parametrize("level", [0.49, 0.96, 90, np.nan])
def test_confidence_interval_rejects_unsupported_levels(level) -> None:
    with pytest.raises(ValueError):
        confidence_interval([1, 2, 3], level)


def test_panel_analytics_uses_sample_standard_deviation() -> None:
    rows = [
        {"name": "A", "params": {"p50": 10, "p95": 100}},
        {"name": "B", "params": {"p50": 20, "p95": 300}},
        {"name": "C", "params": {"p50": 30, "p95": 500}},
    ]
    analytics = panel_analytics(rows)

    assert analytics["p50"].average == 20
    assert analytics["p50"].minimum == 10
    assert analytics["p50"].maximum == 30
    assert analytics["p50"].stddev == pytest.approx(10)
    assert analytics["p50"].count == 3
    assert analytics["p95"].stddev == pytest.approx(200)


def test_panel_analytics_accepts_parameter_models_and_ignores_missing_values() -> None:
    analytics = panel_analytics(
        [LognormalParams(10, 100), {"p50": None, "p95": 300}],
        fields=["p50", "p95", "unused"],
    )

    assert analytics["p50"].average == 10
    assert analytics["p50"].stddev == 0
    assert analytics["p95"].average == 200
    assert analytics["unused"].average is None
    assert analytics["unused"].count == 0


def test_average_panel_params_returns_effective_model_values() -> None:
    averages = average_panel_params([{"p50": 10, "p95": 100}, {"p50": 20, "p95": 300}])

    assert averages == {"p50": 15, "p95": 200}


def test_panel_analytics_rejects_nonfinite_data() -> None:
    with pytest.raises(ValueError, match="finite"):
        panel_analytics([{"p50": np.inf}])
