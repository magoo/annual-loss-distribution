import numpy as np
import pytest
from scipy import stats

from annual_loss import (
    DistributionType,
    LognormalParams,
    ParameterValidationError,
    ParetoParams,
    PertParams,
    distribution_curve,
    distribution_mean,
    fit_lognormal,
    fit_pareto,
    fit_pert,
    frequency_work_rate,
    sample_distribution,
)


def test_lognormal_fit_recovers_input_quantiles() -> None:
    params = LognormalParams(p50=12.0, p95=240.0)
    fit = fit_lognormal(params)
    model = stats.lognorm(s=fit.sigma, scale=np.exp(fit.mu))

    assert model.ppf(0.50) == pytest.approx(params.p50)
    assert model.ppf(0.95) == pytest.approx(params.p95)
    assert fit.sigma > 0


def test_pareto_fit_recovers_input_quantiles() -> None:
    params = ParetoParams(p50=10.0, p95=80.0)
    fit = fit_pareto(params)
    model = stats.pareto(b=fit.shape, scale=fit.scale)

    assert model.ppf(0.50) == pytest.approx(params.p50)
    assert model.ppf(0.95) == pytest.approx(params.p95)
    assert fit.scale > 0
    assert fit.shape > 0


def test_pert_fit_has_requested_support_and_mode() -> None:
    params = PertParams(min=1.0, mode=5.0, max=20.0)
    fit = fit_pert(params)
    beta_mode = (fit.alpha - 1) / (fit.alpha + fit.beta - 2)
    scaled_mode = fit.minimum + (fit.maximum - fit.minimum) * beta_mode

    assert fit.minimum == params.min
    assert fit.maximum == params.max
    assert scaled_mode == pytest.approx(params.mode)
    assert distribution_mean("pert", params) == pytest.approx(
        (params.min + 4 * params.mode + params.max) / 6
    )


@pytest.mark.parametrize(
    ("dist_type", "params"),
    [
        (DistributionType.LOGNORMAL, LognormalParams(5.0, 25.0)),
        (DistributionType.PARETO, ParetoParams(5.0, 25.0)),
        (DistributionType.PERT, PertParams(0.0, 5.0, 25.0)),
    ],
)
def test_distribution_curves_are_finite_and_monotone(dist_type, params) -> None:
    curve = distribution_curve(dist_type, params)

    assert curve.distribution_type is dist_type
    assert curve.x.shape == curve.pdf.shape == curve.cdf.shape == (500,)
    assert np.all(np.isfinite(curve.x))
    assert np.all(np.isfinite(curve.pdf))
    assert np.all(np.isfinite(curve.cdf))
    assert np.all(curve.pdf >= 0)
    assert np.all(np.diff(curve.x) > 0)
    assert np.all(np.diff(curve.cdf) >= 0)
    assert np.all((curve.cdf >= 0) & (curve.cdf <= 1))
    assert curve.y_pdf is curve.pdf
    assert curve.y_cdf is curve.cdf


def test_pert_curve_includes_exact_bounded_support() -> None:
    curve = distribution_curve("pert", {"min": 0, "mode": 2, "max": 9})

    assert curve.x[0] == 0
    assert curve.x[-1] == 9
    assert curve.cdf[0] == 0
    assert curve.cdf[-1] == 1


@pytest.mark.parametrize(
    ("dist_type", "params", "expected_p50", "expected_p95", "p95_tolerance"),
    [
        ("lognormal", {"p50": 10, "p95": 100}, 10, 100, 0.04),
        ("pareto", {"p50": 10, "p95": 100}, 10, 100, 0.06),
    ],
)
def test_seeded_sampling_matches_modeled_quantiles(
    dist_type, params, expected_p50, expected_p95, p95_tolerance
) -> None:
    samples = sample_distribution(dist_type, params, 200_000, np.random.default_rng(20260828))

    p50, p95 = np.quantile(samples, [0.50, 0.95])
    assert p50 == pytest.approx(expected_p50, rel=0.02)
    assert p95 == pytest.approx(expected_p95, rel=p95_tolerance)
    assert np.all(np.isfinite(samples))
    assert np.all(samples >= 0)


def test_pert_sampling_stays_in_support_and_matches_mean() -> None:
    params = PertParams(min=100, mode=250, max=1_000)
    samples = sample_distribution("pert", params, 100_000, np.random.default_rng(7))

    assert np.min(samples) >= params.min
    assert np.max(samples) <= params.max
    assert np.mean(samples) == pytest.approx(distribution_mean("pert", params), rel=0.01)


def test_sampling_is_reproducible_with_explicit_generators() -> None:
    first = sample_distribution("lognormal", {"p50": 5, "p95": 20}, 100, np.random.default_rng(123))
    second = sample_distribution(
        "lognormal", {"p50": 5, "p95": 20}, 100, np.random.default_rng(123)
    )

    np.testing.assert_array_equal(first, second)


def test_direct_sampling_respects_the_hard_draw_limit() -> None:
    with pytest.raises(ValueError, match="1,500,000"):
        sample_distribution(
            "lognormal",
            {"p50": 5, "p95": 20},
            1_500_001,
            np.random.default_rng(123),
        )


def test_infinite_mean_pareto_uses_p95_as_frequency_work_proxy() -> None:
    params = ParetoParams(p50=1, p95=10)

    assert distribution_mean("pareto", params) == float("inf")
    assert frequency_work_rate("pareto", params) == params.p95


@pytest.mark.parametrize(
    ("dist_type", "params"),
    [
        ("lognormal", {"p50": 0, "p95": 10}),
        ("pareto", {"p50": 10, "p95": 10}),
        ("pert", {"min": 1, "mode": 1, "max": 2}),
    ],
)
def test_distribution_curve_rejects_invalid_models(dist_type, params) -> None:
    with pytest.raises(ParameterValidationError):
        distribution_curve(dist_type, params)


def test_distribution_curve_rejects_unsafe_resolution() -> None:
    with pytest.raises(ValueError, match="num_points"):
        distribution_curve("lognormal", {"p50": 1, "p95": 2}, num_points=1)
