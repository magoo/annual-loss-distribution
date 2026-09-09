"""Plotly figures for analytical distributions and Monte Carlo results.

The chart builder is intentionally independent from Marimo so the application can
compose and test figures without starting a notebook server.  It preserves the
important visual semantics of the source application: analytical PDF/CDF curves,
integer frequency bars, log-spaced dollar histograms, empirical step CDFs, and an
explicit annotation for zero-outcome mass.
"""

from __future__ import annotations

from numbers import Real
from typing import Literal, TypeAlias

import numpy as np
import plotly.graph_objects as go

from .models import DistributionCurve, Section, SimulationResult
from .statistics import interpolate_percentile

ChartView: TypeAlias = Literal["pdf", "cdf"]

_PDF_COLOR = "#d84b73"
_CDF_COLOR = "#4f5fbf"
_GRID_COLOR = "rgba(100, 116, 139, 0.16)"
_ZERO_LINE_COLOR = "rgba(100, 116, 139, 0.28)"
_SECTION_LABELS = {
    Section.FREQUENCY: ("Frequency Distribution", "Incidents per Year"),
    Section.COST: ("Cost Distribution", "Cost per Incident"),
    Section.LOSS: ("Annual Loss Distribution", "Annual Loss"),
}


def build_distribution_figure(
    data: DistributionCurve | SimulationResult,
    *,
    view: ChartView = "pdf",
    use_dollars: bool = False,
    section: Section | str | None = None,
    focus_percentile: float = 99.5,
) -> go.Figure:
    """Build a Plotly PDF/histogram or CDF figure for model output.

    ``focus_percentile`` accepts either a probability from 0.95 through 1.0 or
    a percentage from 95 through 100.  A value of 1 or 100 shows the full plotted
    range.  For simulation results, an omitted ``section`` uses ``data.kind``;
    analytical curves default to Frequency unless a section is supplied.
    """

    if not isinstance(data, (DistributionCurve, SimulationResult)):
        raise TypeError("data must be a DistributionCurve or SimulationResult")
    if view not in ("pdf", "cdf"):
        raise ValueError("view must be 'pdf' or 'cdf'")
    if not isinstance(use_dollars, bool):
        raise TypeError("use_dollars must be a boolean")

    resolved_section = _coerce_section(section, data)
    focus_probability = _coerce_focus_percentile(focus_percentile)
    _validate_chart_data(data)

    if isinstance(data, SimulationResult):
        figure = _simulation_figure(
            data,
            view=view,
            use_dollars=use_dollars,
            section=resolved_section,
        )
    else:
        figure = _analytical_figure(
            data,
            view=view,
            use_dollars=use_dollars,
            section=resolved_section,
        )

    _apply_layout(
        figure,
        data=data,
        view=view,
        use_dollars=use_dollars,
        section=resolved_section,
        focus_probability=focus_probability,
    )
    if isinstance(data, SimulationResult):
        _annotate_zero_mass(figure, data, use_dollars, resolved_section)
    return figure


def _coerce_section(
    section: Section | str | None,
    data: DistributionCurve | SimulationResult,
) -> Section:
    if section is None:
        section = data.kind if isinstance(data, SimulationResult) else Section.FREQUENCY
    try:
        return Section(section)
    except (TypeError, ValueError) as exc:
        choices = ", ".join(item.value for item in Section)
        raise ValueError(f"unsupported section {section!r}; choose {choices}") from exc


def _coerce_focus_percentile(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("focus_percentile must be a number")
    numeric = float(value)
    if not np.isfinite(numeric):
        raise ValueError("focus_percentile must be finite")
    probability = numeric if numeric <= 1 else numeric / 100.0
    if not 0.95 <= probability <= 1.0:
        raise ValueError("focus_percentile must be between 0.95 and 1, or 95 and 100")
    return probability


def _validate_chart_data(data: DistributionCurve | SimulationResult) -> None:
    if isinstance(data, DistributionCurve):
        x = np.asarray(data.x, dtype=np.float64)
        pdf = np.asarray(data.pdf, dtype=np.float64)
        cdf = np.asarray(data.cdf, dtype=np.float64)
        if x.ndim != 1 or pdf.ndim != 1 or cdf.ndim != 1:
            raise ValueError("distribution curve arrays must be one-dimensional")
        if x.size == 0 or x.size != pdf.size or x.size != cdf.size:
            raise ValueError("distribution curve arrays must be non-empty and equal-length")
        if (
            not np.all(np.isfinite(x))
            or not np.all(np.isfinite(pdf))
            or not np.all(np.isfinite(cdf))
        ):
            raise ValueError("distribution curve arrays must contain only finite values")
        if np.any(x[1:] < x[:-1]) or np.any(pdf < 0):
            raise ValueError(
                "distribution curve x must increase and PDF values must be non-negative"
            )
    else:
        samples = np.asarray(data.samples, dtype=np.float64)
        x = np.asarray(data.cdf.x, dtype=np.float64)
        cdf = np.asarray(data.cdf.probabilities, dtype=np.float64)
        if samples.ndim != 1 or samples.size == 0:
            raise ValueError("simulation samples must be a non-empty one-dimensional array")
        if not np.all(np.isfinite(samples)) or np.any(samples < 0):
            raise ValueError("simulation samples must contain finite, non-negative values")
        if x.ndim != 1 or cdf.ndim != 1 or x.size == 0 or x.size != cdf.size:
            raise ValueError("empirical CDF arrays must be non-empty and equal-length")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(cdf)):
            raise ValueError("empirical CDF arrays must contain only finite values")

    if np.any(x < 0):
        raise ValueError("chart x coordinates must be non-negative")
    if np.any(x[1:] < x[:-1]) or np.any(cdf[1:] < cdf[:-1]):
        raise ValueError("CDF coordinates must be non-decreasing")
    if np.any((cdf < 0) | (cdf > 1)):
        raise ValueError("CDF probabilities must be between 0 and 1")


def _analytical_figure(
    curve: DistributionCurve,
    *,
    view: ChartView,
    use_dollars: bool,
    section: Section,
) -> go.Figure:
    cdf = np.asarray(curve.cdf, dtype=np.float64)
    y = np.asarray(curve.pdf if view == "pdf" else curve.cdf, dtype=np.float64)
    customdata = np.column_stack((cdf, 1.0 - cdf)).tolist()
    trace = go.Scatter(
        x=np.asarray(curve.x, dtype=np.float64),
        y=y,
        type="scatter",
        mode="lines",
        line={"color": _PDF_COLOR if view == "pdf" else _CDF_COLOR, "width": 2.5},
        fill="tozeroy" if view == "pdf" else None,
        fillcolor="rgba(247, 37, 133, 0.12)" if view == "pdf" else None,
        customdata=customdata,
        hovertemplate=_hover_template(use_dollars, section),
        name="",
    )
    return go.Figure(data=[trace])


def _simulation_figure(
    result: SimulationResult,
    *,
    view: ChartView,
    use_dollars: bool,
    section: Section,
) -> go.Figure:
    if view == "cdf":
        return _empirical_cdf_figure(result, use_dollars=use_dollars, section=section)

    samples = np.asarray(result.samples, dtype=np.float64)
    if use_dollars:
        return _dollar_histogram_figure(result, section=section)

    if section is Section.FREQUENCY and np.all(samples == np.floor(samples)):
        values, counts = np.unique(samples, return_counts=True)
        cdf_values = _cdf_at(result, values)
        customdata = np.column_stack((cdf_values, 1.0 - cdf_values, counts / samples.size)).tolist()
        trace = go.Bar(
            x=values,
            y=counts,
            width=0.8,
            marker=_bar_marker(),
            customdata=customdata,
            hovertemplate=_histogram_hover_template(use_dollars, section),
            name="",
        )
        return go.Figure(data=[trace])

    trace = go.Histogram(
        x=samples,
        marker=_bar_marker(),
        hovertemplate="%{x:,.2f}<br>Simulated outcomes: %{y:,}<extra></extra>",
        name="",
    )
    return go.Figure(data=[trace])


def _empirical_cdf_figure(
    result: SimulationResult,
    *,
    use_dollars: bool,
    section: Section,
) -> go.Figure:
    x = np.asarray(result.cdf.x, dtype=np.float64)
    probabilities = np.asarray(result.cdf.probabilities, dtype=np.float64)
    if use_dollars and np.any(x > 0):
        visible = x > 0
        x = x[visible]
        probabilities = probabilities[visible]

    customdata = np.column_stack((probabilities, 1.0 - probabilities)).tolist()
    trace = go.Scatter(
        x=x,
        y=probabilities,
        type="scatter",
        mode="lines",
        line={"color": _CDF_COLOR, "width": 2.5, "shape": "hv"},
        customdata=customdata,
        hovertemplate=_hover_template(use_dollars, section),
        name="",
    )
    return go.Figure(data=[trace])


def _dollar_histogram_figure(result: SimulationResult, *, section: Section) -> go.Figure:
    samples = np.asarray(result.samples, dtype=np.float64)
    positive = samples[samples > 0]

    if positive.size == 0:
        values = np.asarray([0.0])
        counts = np.asarray([samples.size], dtype=np.int64)
        widths: np.ndarray | None = None
    else:
        lower, upper = np.quantile(positive, (0.005, 0.995))
        if upper <= lower:
            lower, upper = float(np.min(positive)), float(np.max(positive))

        if upper > lower > 0:
            edges = np.geomspace(lower, upper, 61, dtype=np.float64)
            counts, _ = np.histogram(np.clip(positive, lower, upper), bins=edges)
            values = np.sqrt(edges[:-1] * edges[1:])
            widths = np.diff(edges)
        else:
            values = np.asarray([float(positive[0])], dtype=np.float64)
            counts = np.asarray([positive.size], dtype=np.int64)
            widths = None

    cdf_values = _cdf_at(result, values)
    customdata = np.column_stack((cdf_values, 1.0 - cdf_values, counts / samples.size)).tolist()
    trace = go.Bar(
        x=values,
        y=counts,
        width=widths,
        marker=_bar_marker(),
        customdata=customdata,
        hovertemplate=_histogram_hover_template(True, section),
        name="",
    )
    return go.Figure(data=[trace])


def _cdf_at(result: SimulationResult, x: np.ndarray) -> np.ndarray:
    return np.interp(
        x,
        np.asarray(result.cdf.x, dtype=np.float64),
        np.asarray(result.cdf.probabilities, dtype=np.float64),
    )


def _bar_marker() -> dict[str, object]:
    return {
        "color": "rgba(216, 75, 115, 0.42)",
        "line": {"color": _PDF_COLOR, "width": 0.8},
    }


def _hover_template(use_dollars: bool, section: Section) -> str:
    value = "$%{x:,.0f}" if use_dollars else "%{x:,.2f}"
    lines = [value, "Percentile: %{customdata[0]:.1%}"]
    if section is Section.LOSS:
        lines.append("%{customdata[1]:.1%} chance of losing more")
    return "<br>".join(lines) + "<extra></extra>"


def _histogram_hover_template(use_dollars: bool, section: Section) -> str:
    value = "$%{x:,.0f}" if use_dollars else "%{x:,.0f} incidents"
    lines = [value, "Outcome share: %{customdata[2]:.1%}"]
    if section is Section.LOSS:
        lines.extend(
            (
                "Percentile: %{customdata[0]:.1%}",
                "%{customdata[1]:.1%} chance of losing more",
            )
        )
    return "<br>".join(lines) + "<extra></extra>"


def _apply_layout(
    figure: go.Figure,
    *,
    data: DistributionCurve | SimulationResult,
    view: ChartView,
    use_dollars: bool,
    section: Section,
    focus_probability: float,
) -> None:
    section_title, x_axis_title = _SECTION_LABELS[section]
    y_axis_title = (
        "Simulated Outcomes"
        if view == "pdf" and isinstance(data, SimulationResult)
        else "Likelihood"
        if view == "pdf"
        else "Cumulative Probability"
    )
    log_x_axis = (
        isinstance(data, SimulationResult)
        and use_dollars
        and np.any(np.asarray(data.samples, dtype=np.float64) > 0)
    )
    focused_range = _focused_range(data, focus_probability, use_dollars)
    if focused_range is not None and log_x_axis:
        focused_range = (np.log10(focused_range[0]), np.log10(focused_range[1]))

    tick_format = ",.0f" if use_dollars or section is Section.FREQUENCY else ",.2f"
    figure.update_layout(
        template="plotly_white",
        autosize=True,
        height=360,
        font={
            "family": "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
            "size": 12,
        },
        title={
            "text": section_title,
            "x": 0.01,
            "xanchor": "left",
            "font": {"size": 18},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 48, "r": 16, "b": 52, "l": 56},
        showlegend=False,
        hovermode="closest",
        bargap=0,
        xaxis={
            "title": {"text": x_axis_title, "font": {"size": 12}, "standoff": 12},
            "type": "log" if log_x_axis else "linear",
            "range": focused_range,
            "tickprefix": "$" if use_dollars else "",
            "tickformat": tick_format,
            "gridcolor": _GRID_COLOR,
            "zerolinecolor": _ZERO_LINE_COLOR,
            "automargin": True,
        },
        yaxis={
            "title": {"text": y_axis_title, "font": {"size": 12}, "standoff": 10},
            "range": [0, 1.05] if view == "cdf" else None,
            "showticklabels": not (view == "pdf" and isinstance(data, DistributionCurve)),
            "gridcolor": _GRID_COLOR,
            "zerolinecolor": _ZERO_LINE_COLOR,
            "tickformat": ".0%" if view == "cdf" else ",d",
            "automargin": True,
        },
        hoverlabel={"bgcolor": "#202534", "font": {"color": "#ffffff", "size": 12}},
    )


def _focused_range(
    data: DistributionCurve | SimulationResult,
    probability: float,
    use_dollars: bool,
) -> tuple[float, float] | None:
    if probability >= 1.0:
        return None

    if isinstance(data, SimulationResult):
        x = np.asarray(data.cdf.x, dtype=np.float64)
        cdf = np.asarray(data.cdf.probabilities, dtype=np.float64)
    else:
        x = np.asarray(data.x, dtype=np.float64)
        cdf = np.asarray(data.cdf, dtype=np.float64)

    lower = interpolate_percentile(x, cdf, 0.005)
    upper = interpolate_percentile(x, cdf, probability)
    if use_dollars and lower <= 0:
        positive = x[x > 0]
        if positive.size == 0:
            return None
        lower = float(positive[0])
    if not np.isfinite(lower) or not np.isfinite(upper) or upper <= lower:
        return None
    return float(lower), float(upper)


def _annotate_zero_mass(
    figure: go.Figure,
    result: SimulationResult,
    use_dollars: bool,
    section: Section,
) -> None:
    samples = np.asarray(result.samples, dtype=np.float64)
    zero_share = float(np.count_nonzero(samples == 0) / samples.size)
    if zero_share <= 0:
        return

    if section is Section.FREQUENCY and not use_dollars:
        text = f"{zero_share:.1%} of simulated years have 0 incidents"
    else:
        zero = "$0" if use_dollars else "0"
        text = f"{zero_share:.1%} of simulated outcomes are {zero}"
    figure.add_annotation(
        text=text,
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.99,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#e5e7eb",
        borderpad=6,
        font={"size": 12, "color": "#6b7280"},
    )
