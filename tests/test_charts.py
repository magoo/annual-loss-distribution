from __future__ import annotations

import marimo as mo
import numpy as np
import pytest
from plotly import graph_objects as go

from annual_loss.charts import build_distribution_figure
from annual_loss.models import (
    DistributionCurve,
    DistributionType,
    EmpiricalCDF,
    Section,
    SimulationResult,
)
from annual_loss.statistics import empirical_cdf


def curve() -> DistributionCurve:
    return DistributionCurve(
        distribution_type=DistributionType.PERT,
        x=np.asarray([0.0, 10.0, 20.0, 30.0]),
        pdf=np.asarray([0.0, 0.04, 0.02, 0.0]),
        cdf=np.asarray([0.0, 0.25, 0.75, 1.0]),
    )


def result(samples: list[float], kind: Section) -> SimulationResult:
    values = np.asarray(samples, dtype=np.float64)
    return SimulationResult(
        samples=values,
        cdf=empirical_cdf(values),
        num_rounds=values.size,
        seed=12345,
        total_event_draws=0,
        kind=kind,
    )


def test_analytical_pdf_uses_density_curve_currency_and_section_labels() -> None:
    figure = build_distribution_figure(
        curve(),
        view="pdf",
        use_dollars=True,
        section="cost",
        focus_percentile=99.5,
    )

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "scatter"
    np.testing.assert_array_equal(figure.data[0].y, curve().pdf)
    assert figure.data[0].fill == "tozeroy"
    assert figure.layout.title.text == "Cost Distribution"
    assert figure.layout.xaxis.title.text == "Cost per Incident"
    assert figure.layout.xaxis.tickprefix == "$"
    assert figure.layout.yaxis.title.text == "Likelihood"
    assert figure.layout.yaxis.showticklabels is False


def test_analytical_cdf_uses_cumulative_values_and_percentage_axis() -> None:
    figure = build_distribution_figure(
        curve(), view="cdf", section=Section.FREQUENCY, focus_percentile=100
    )

    np.testing.assert_array_equal(figure.data[0].y, curve().cdf)
    assert figure.data[0].fill is None
    assert figure.layout.xaxis.title.text == "Incidents per Year"
    assert figure.layout.xaxis.range is None
    assert tuple(figure.layout.yaxis.range) == (0, 1.05)
    assert figure.layout.yaxis.tickformat == ".0%"


def test_chart_layout_uses_compact_editorial_theme() -> None:
    figure = build_distribution_figure(
        curve(), view="pdf", section=Section.COST, focus_percentile=100
    )

    assert figure.layout.autosize is True
    assert figure.layout.height == 360
    assert figure.layout.margin.to_plotly_json() == {"t": 48, "r": 16, "b": 52, "l": 56}
    assert figure.layout.font.family.startswith("ui-sans-serif")
    assert figure.layout.title.font.size == 18
    assert figure.layout.xaxis.gridcolor == "rgba(100, 116, 139, 0.16)"
    assert figure.layout.yaxis.zerolinecolor == "rgba(100, 116, 139, 0.28)"
    assert figure.data[0].line.color == "#d84b73"


def test_frequency_pdf_counts_each_integer_as_a_bar() -> None:
    simulation = result([0, 1, 1, 2, 2, 2], Section.FREQUENCY)

    figure = build_distribution_figure(simulation, view="pdf")

    assert figure.data[0].type == "bar"
    np.testing.assert_array_equal(figure.data[0].x, [0, 1, 2])
    np.testing.assert_array_equal(figure.data[0].y, [1, 2, 3])
    assert figure.data[0].width == 0.8
    assert figure.layout.xaxis.type == "linear"
    assert figure.layout.yaxis.title.text == "Simulated Outcomes"
    assert figure.data[0].marker.color == "rgba(216, 75, 115, 0.42)"
    assert figure.data[0].marker.line.width == 0.8
    assert "0 incidents" in figure.layout.annotations[0].text


def test_empirical_cdf_is_rendered_as_a_step_function() -> None:
    simulation = result([0, 1, 1, 3, 8], Section.FREQUENCY)

    figure = build_distribution_figure(simulation, view="cdf", focus_percentile=100)

    assert figure.data[0].type == "scatter"
    assert figure.data[0].line.shape == "hv"
    np.testing.assert_array_equal(figure.data[0].x, simulation.cdf.x)
    np.testing.assert_array_equal(figure.data[0].y, simulation.cdf.probabilities)
    assert tuple(figure.layout.yaxis.range) == (0, 1.05)


def test_dollar_pdf_uses_log_spaced_bars_and_preserves_positive_counts() -> None:
    samples = np.geomspace(100, 1_000_000, 1_000).tolist()
    simulation = result([0] * 100 + samples, Section.LOSS)

    figure = build_distribution_figure(
        simulation,
        view="pdf",
        use_dollars=True,
        focus_percentile=99.5,
    )

    trace = figure.data[0]
    assert trace.type == "bar"
    assert len(trace.x) == 60
    assert sum(trace.y) == 1_000
    ratios = np.asarray(trace.x[1:]) / np.asarray(trace.x[:-1])
    assert np.allclose(ratios, ratios[0])
    assert figure.layout.xaxis.type == "log"
    assert figure.layout.xaxis.title.text == "Annual Loss"
    assert "9.1% of simulated outcomes are $0" == figure.layout.annotations[0].text
    assert "chance of losing more" in trace.hovertemplate


def test_dollar_histogram_selection_is_safe_for_marimo() -> None:
    samples = np.geomspace(100, 1_000_000, 1_000).tolist()
    simulation = result([0] * 100 + samples, Section.LOSS)
    figure = build_distribution_figure(
        simulation,
        view="pdf",
        use_dollars=True,
        focus_percentile=99.5,
    )
    trace = figure.data[0]

    assert isinstance(trace.customdata[0], list)
    assert len(trace.customdata[0]) == 3
    metadata = np.asarray(trace.customdata, dtype=np.float64)
    np.testing.assert_allclose(metadata[:, 0] + metadata[:, 1], 1.0)
    np.testing.assert_allclose(metadata[:, 2], np.asarray(trace.y) / simulation.samples.size)

    plot = mo.ui.plotly(figure)
    selected = plot._convert_value(
        {
            "points": [],
            "indices": [],
            "range": {
                "x": [float(np.min(trace.x)), float(np.max(trace.x))],
                "y": [0, int(np.max(trace.y))],
            },
        }
    )

    assert len(selected) == len(trace.x)
    assert all(isinstance(point["customdata"], list) for point in selected)


@pytest.mark.parametrize(
    ("samples", "section", "use_dollars"),
    [
        ([0, 1, 1, 2, 2, 2], Section.FREQUENCY, False),
        ([0, 0, 0, 0], Section.LOSS, True),
    ],
)
def test_other_bar_selections_are_safe_for_marimo(
    samples: list[float], section: Section, use_dollars: bool
) -> None:
    figure = build_distribution_figure(
        result(samples, section), view="pdf", use_dollars=use_dollars
    )
    trace = figure.data[0]
    plot = mo.ui.plotly(figure)

    selected = plot._convert_value(
        {
            "points": [],
            "indices": [],
            "range": {
                "x": [float(np.min(trace.x)), float(np.max(trace.x))],
                "y": [0, int(np.max(trace.y))],
            },
        }
    )

    assert selected
    assert all(isinstance(point["customdata"], list) for point in selected)


def test_dollar_cdf_omits_zero_on_log_axis_but_annotates_its_mass() -> None:
    simulation = result([0, 0, 100, 200], Section.LOSS)

    figure = build_distribution_figure(
        simulation, view="cdf", use_dollars=True, focus_percentile=100
    )

    assert np.all(np.asarray(figure.data[0].x) > 0)
    assert figure.layout.xaxis.type == "log"
    assert figure.layout.annotations[0].text == "50.0% of simulated outcomes are $0"


@pytest.mark.parametrize("view", ["pdf", "cdf"])
def test_all_zero_dollar_results_are_safe_and_use_a_linear_axis(view: str) -> None:
    simulation = result([0, 0, 0, 0], Section.LOSS)

    figure = build_distribution_figure(
        simulation, view=view, use_dollars=True, focus_percentile=99.5
    )

    assert figure.layout.xaxis.type == "linear"
    assert figure.layout.xaxis.range is None
    assert figure.layout.annotations[0].text == "100.0% of simulated outcomes are $0"
    if view == "pdf":
        np.testing.assert_array_equal(figure.data[0].x, [0])
        np.testing.assert_array_equal(figure.data[0].y, [4])
    else:
        np.testing.assert_array_equal(figure.data[0].x, [0])
        np.testing.assert_array_equal(figure.data[0].y, [1])


def test_degenerate_positive_dollar_result_uses_one_safe_bar() -> None:
    figure = build_distribution_figure(
        result([500, 500, 500], Section.COST),
        view="pdf",
        use_dollars=True,
    )

    np.testing.assert_array_equal(figure.data[0].x, [500])
    np.testing.assert_array_equal(figure.data[0].y, [3])
    assert figure.layout.xaxis.type == "log"
    assert figure.layout.xaxis.range is None


def test_fraction_and_percentage_focus_values_produce_the_same_range() -> None:
    simulation = result(list(range(1, 101)), Section.FREQUENCY)

    fraction = build_distribution_figure(simulation, focus_percentile=0.95)
    percentage = build_distribution_figure(simulation, focus_percentile=95)

    assert tuple(fraction.layout.xaxis.range) == tuple(percentage.layout.xaxis.range)


@pytest.mark.parametrize("view", ["density", "PDF", ""])
def test_unknown_view_is_rejected(view: str) -> None:
    with pytest.raises(ValueError, match="view"):
        build_distribution_figure(curve(), view=view)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [94.9, 100.1, 0.5, float("nan"), True])
def test_invalid_focus_percentiles_are_rejected(value: float) -> None:
    expected = TypeError if value is True else ValueError
    with pytest.raises(expected, match="focus_percentile"):
        build_distribution_figure(curve(), focus_percentile=value)


def test_invalid_section_and_malformed_arrays_are_rejected() -> None:
    with pytest.raises(ValueError, match="section"):
        build_distribution_figure(curve(), section="unknown")

    malformed = DistributionCurve(
        distribution_type=DistributionType.PERT,
        x=np.asarray([0.0, 1.0]),
        pdf=np.asarray([1.0]),
        cdf=np.asarray([0.0, 1.0]),
    )
    with pytest.raises(ValueError, match="equal-length"):
        build_distribution_figure(malformed)


def test_invalid_result_kind_is_reported_as_a_section_error() -> None:
    simulation = result([1, 2, 3], Section.FREQUENCY)
    object.__setattr__(simulation, "kind", "unknown")

    with pytest.raises(ValueError, match="section"):
        build_distribution_figure(simulation)


def test_manually_constructed_degenerate_empirical_cdf_is_supported() -> None:
    simulation = SimulationResult(
        samples=np.asarray([7.0, 7.0]),
        cdf=EmpiricalCDF(x=np.asarray([7.0]), probabilities=np.asarray([1.0])),
        num_rounds=2,
        seed=1,
        total_event_draws=0,
        kind=Section.COST,
    )

    figure = build_distribution_figure(simulation, view="cdf", use_dollars=True)

    np.testing.assert_array_equal(figure.data[0].x, [7])
    np.testing.assert_array_equal(figure.data[0].y, [1])
    assert figure.layout.xaxis.range is None
