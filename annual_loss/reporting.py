"""Plain-language reporting for annual-loss simulations.

This module contains presentation logic only. Statistical calculations remain
in :mod:`annual_loss.statistics`, which lets the Marimo notebook and other
callers use one trusted implementation for percentiles and panel statistics.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

from .formatting import EM_DASH, format_compact, format_value
from .statistics import confidence_interval

_DISTRIBUTION_LABELS = {
    "lognormal": "Lognormal",
    "pert": "PERT",
    "pareto": "Pareto",
}

_SECTION_GUIDANCE = {
    "frequency": (
        "Use this section to estimate how many incidents you expect over the next year. "
        "These annual incident counts become the Frequency input for the Monte Carlo "
        "simulation that estimates total yearly losses."
    ),
    "cost": (
        "Use this section to estimate the typical and high-end cost of a single incident. "
        "These per-incident loss values become the Cost input for the Monte Carlo "
        "simulation that estimates total yearly losses."
    ),
}


@dataclass(frozen=True, slots=True)
class ReportSection:
    """A titled collection of executive-report bullets."""

    title: str
    bullets: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation for UI rendering."""

        return {"title": self.title, "bullets": list(self.bullets)}


@dataclass(frozen=True, slots=True)
class PlainDescription:
    """Short guidance shown before the Calculate step."""

    text: str

    @property
    def mode(self) -> str:
        return "plain"

    def as_dict(self) -> dict[str, str]:
        return {"mode": self.mode, "text": self.text}


@dataclass(frozen=True, slots=True)
class ExecutiveSummary:
    """Structured and copy-ready forms of the Calculate-step report."""

    title: str
    intro: str
    confidence_narrative: tuple[str, ...]
    sections: tuple[ReportSection, ...]
    copy_text: str
    markdown: str

    @property
    def mode(self) -> str:
        return "executive"

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation for Marimo or API consumers."""

        return {
            "mode": self.mode,
            "title": self.title,
            "intro": self.intro,
            "confidence_narrative": list(self.confidence_narrative),
            "sections": [section.as_dict() for section in self.sections],
            "copy_text": self.copy_text,
            "markdown": self.markdown,
        }


def _field(record: object, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(record, Mapping) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return default


def _as_tuple(values: Iterable[object] | None) -> tuple[object, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    return tuple(values)


def _distribution_key(value: object) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value).strip().lower().replace("_", "-")


def _distribution_label(value: object) -> str:
    key = _distribution_key(value)
    return _DISTRIBUTION_LABELS.get(key, key.replace("-", " ").title() or "Lognormal")


def _model_params(value: object | None) -> object:
    if value is None:
        return {}
    nested = _field(value, "params", "parameters")
    return nested if nested is not None else value


def _param(params: object, *names: str) -> Any:
    return _field(_model_params(params), *names)


def _format_param(value: object, use_dollars: bool) -> str:
    rendered = format_compact(value, use_dollars=use_dollars)
    return "n/a" if rendered == EM_DASH else rendered


def _format_incident_bound(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not isfinite(number):
        return "n/a"

    # Confidence bounds for frequency are presented as whole incident counts,
    # matching the discrete yearly-count model used by the simulation.
    rounded = int(max(0.0, number) + 0.5)
    rendered = format_compact(rounded, use_dollars=False)
    return "n/a" if rendered == EM_DASH else rendered


def _normalise_confidence_level(level: object) -> float:
    try:
        numeric = float(level)
    except (TypeError, ValueError) as error:
        raise ValueError("confidence level must be a number") from error

    if numeric > 1:
        numeric /= 100
    if not isfinite(numeric) or not 0.50 <= numeric <= 0.95:
        raise ValueError("confidence level must be between 0.50 and 0.95, or 50 and 95")
    return numeric


def _interval_for(data: object | None, level: float) -> object | None:
    if data is None:
        return None
    try:
        return confidence_interval(data, level=level)
    except (TypeError, ValueError):
        return None


def _interval_value(interval: object | None, name: str) -> Any:
    if interval is None:
        return None
    return _field(interval, name)


def _confidence_label(level: float) -> str:
    return f"{format_value(level * 100)}%"


def confidence_statement(
    data: object,
    *,
    section: str = "loss",
    confidence_level: float = 0.90,
    use_dollars: bool | None = None,
) -> str:
    """Build the copyable range statement shown beneath a result chart.

    ``data`` may be any input accepted by
    :func:`annual_loss.statistics.confidence_interval`, including a
    ``SimulationResult``, ``EmpiricalCDF``, or one-dimensional sample array.
    """

    level = _normalise_confidence_level(confidence_level)
    interval = _interval_for(data, level)
    if interval is None:
        raise ValueError("confidence statement requires non-empty finite result data")

    section_key = str(section).strip().lower()
    section_nouns = {
        "frequency": "incidents per year",
        "cost": "incident costs",
        "loss": "annual losses",
    }
    if section_key not in section_nouns:
        raise ValueError("section must be 'frequency', 'cost', or 'loss'")

    dollars = section_key != "frequency" if use_dollars is None else use_dollars
    lower = format_compact(_interval_value(interval, "lower"), dollars)
    median = format_compact(_interval_value(interval, "median"), dollars)
    upper = format_compact(_interval_value(interval, "upper"), dollars)

    return (
        f"The central {_confidence_label(level)} of modeled {section_nouns[section_key]} "
        f"fall between {lower} and {upper}, with a median of {median}."
    )


def confidence_narrative(
    *,
    frequency_result: object | None,
    cost_result: object | None,
    loss_result: object | None,
    confidence_level: float = 0.90,
) -> tuple[str, str, str]:
    """Return the three source-compatible executive confidence statements."""

    level = _normalise_confidence_level(confidence_level)
    confidence_label = _confidence_label(level)
    frequency_interval = _interval_for(frequency_result, level)
    cost_interval = _interval_for(cost_result, level)
    loss_interval = _interval_for(loss_result, level)

    incident_lower = _format_incident_bound(_interval_value(frequency_interval, "lower"))
    incident_upper = _format_incident_bound(_interval_value(frequency_interval, "upper"))
    cost_lower = _format_param(_interval_value(cost_interval, "lower"), True)
    cost_upper = _format_param(_interval_value(cost_interval, "upper"), True)
    loss_lower = _format_param(_interval_value(loss_interval, "lower"), True)
    loss_upper = _format_param(_interval_value(loss_interval, "upper"), True)

    return (
        f"The central {confidence_label} of modeled annual incident counts range between "
        f"{incident_lower} and {incident_upper} incidents.",
        f"The central {confidence_label} of modeled per-incident costs range between "
        f"{cost_lower} and {cost_upper}.",
        f"The central {confidence_label} of modeled annual losses range between "
        f"{loss_lower} and {loss_upper}.",
    )


def _scenario_count_label(scenarios: tuple[object, ...]) -> str:
    count = len(scenarios)
    suffix = "" if count == 1 else "s"
    return f"{count} threat scenario{suffix}"


def _clean_name(value: object) -> str:
    return " ".join(str(value).split())


def _scenario_names(scenarios: tuple[object, ...]) -> str:
    names = [
        _clean_name(name)
        for scenario in scenarios
        if (name := _field(scenario, "name")) is not None and _clean_name(name)
    ]
    return ", ".join(names) if names else "Unnamed scenarios"


def simulation_intro(
    *,
    frequency_scenario_mode: bool = False,
    cost_scenario_mode: bool = False,
) -> str:
    """Describe the overall Monte Carlo mode in executive language."""

    if frequency_scenario_mode and cost_scenario_mode:
        return (
            "This executive summary reflects a scenario-based Monte Carlo model that "
            "simulates up to 10,000 potential years of loss outcomes."
        )
    if frequency_scenario_mode or cost_scenario_mode:
        return (
            "This executive summary reflects a hybrid Monte Carlo model that simulates "
            "up to 10,000 potential years and combines scenario-driven inputs with "
            "distribution-driven inputs."
        )
    return (
        "This executive summary reflects a Monte Carlo model of up to 100,000 potential "
        "years that combines incident frequency and incident cost to estimate annual loss "
        "outcomes."
    )


def simulation_setup_bullets(
    *,
    frequency_scenario_mode: bool = False,
    cost_scenario_mode: bool = False,
    scenarios: Iterable[object] | None = None,
) -> tuple[str, ...]:
    """Describe the simulation method and any named scenario set."""

    scenario_items = _as_tuple(scenarios)
    count_label = _scenario_count_label(scenario_items)
    names = _scenario_names(scenario_items)

    if frequency_scenario_mode and cost_scenario_mode:
        return (
            "Simulation mode: Up to 10,000-round scenario-based Monte Carlo",
            f"Scenario set: {count_label} ({names})",
        )
    if frequency_scenario_mode:
        return (
            "Simulation mode: Up to 10,000-round hybrid Monte Carlo",
            f"Scenario set: Frequency sampled from {count_label} ({names})",
            "Cost modeling: Distribution-based",
        )
    if cost_scenario_mode:
        return (
            "Simulation mode: Up to 10,000-round hybrid Monte Carlo",
            f"Scenario set: Cost sampled from {count_label} ({names})",
            "Frequency modeling: Distribution-based",
        )
    return (
        "Simulation mode: Up to 100,000-round distribution-based Monte Carlo",
        "Method: Frequency is sampled as an incident count, then independent per-incident "
        "costs are summed for each simulated year",
    )


def _input_source_bullet(
    panel_active: bool | None,
    panelists: tuple[object, ...],
) -> str:
    active = len(panelists) >= 2 if panel_active is None else panel_active
    if not active or not panelists:
        return "Input source: direct analyst estimate"

    names = [
        _clean_name(name)
        for panelist in panelists
        if (name := _field(panelist, "name")) is not None and _clean_name(name)
    ]
    count = len(panelists)
    expert_label = "expert" if count == 1 else "experts"
    if names:
        return f"Input source: panel of {count} {expert_label} ({', '.join(names)})"
    return f"Input source: panel of {count} {expert_label}"


def _distribution_bullets(
    params: object | None,
    distribution: object,
    *,
    use_dollars: bool,
) -> tuple[str, ...]:
    distribution_key = _distribution_key(distribution)
    label = _distribution_label(distribution)
    bullets = [f"Distribution: {label}"]

    if distribution_key == "pert":
        bullets.extend(
            (
                f"Minimum: {_format_param(_param(params, 'min', 'minimum'), use_dollars)}",
                f"Most likely: {_format_param(_param(params, 'mode', 'most_likely'), use_dollars)}",
                f"Maximum: {_format_param(_param(params, 'max', 'maximum'), use_dollars)}",
            )
        )
    else:
        bullets.extend(
            (
                f"P50 (typical): {_format_param(_param(params, 'p50'), use_dollars)}",
                f"P95 (high): {_format_param(_param(params, 'p95'), use_dollars)}",
            )
        )
    return tuple(bullets)


def _copy_text(
    title: str,
    intro: str,
    confidence_lines: tuple[str, ...],
    sections: tuple[ReportSection, ...],
) -> str:
    lines = [title, intro, "", "Modeled Outcome Ranges:"]
    lines.extend(f"- {line}" for line in confidence_lines)
    for section in sections:
        lines.append(f"{section.title}:")
        lines.extend(f"- {bullet}" for bullet in section.bullets)
    return "\n".join(lines)


def _markdown_text(
    title: str,
    intro: str,
    confidence_lines: tuple[str, ...],
    sections: tuple[ReportSection, ...],
) -> str:
    blocks = [f"## {title}", intro, "### Modeled Outcome Ranges"]
    blocks.append("\n".join(f"- {line}" for line in confidence_lines))
    for section in sections:
        blocks.append(f"### {section.title}")
        blocks.append("\n".join(f"- {bullet}" for bullet in section.bullets))
    return "\n\n".join(blocks)


def build_executive_summary(
    *,
    frequency_params: object | None = None,
    cost_params: object | None = None,
    frequency_distribution: object = "lognormal",
    cost_distribution: object = "lognormal",
    frequency_result: object | None = None,
    cost_result: object | None = None,
    loss_result: object | None = None,
    confidence_level: float = 0.90,
    frequency_scenario_mode: bool = False,
    cost_scenario_mode: bool = False,
    scenarios: Iterable[object] | None = None,
    frequency_panel_active: bool | None = None,
    cost_panel_active: bool | None = None,
    frequency_panelists: Iterable[object] | None = None,
    cost_panelists: Iterable[object] | None = None,
) -> ExecutiveSummary:
    """Create the structured, Markdown, and copy-ready executive report.

    Configuration and participant inputs may be mappings or dataclass-like
    objects. Result inputs are delegated to ``statistics.confidence_interval``.
    Supplying no result for a section produces an explicit ``n/a`` range while
    retaining the model setup narrative.
    """

    scenario_items = _as_tuple(scenarios)
    frequency_panel_items = _as_tuple(frequency_panelists)
    cost_panel_items = _as_tuple(cost_panelists)
    intro = simulation_intro(
        frequency_scenario_mode=frequency_scenario_mode,
        cost_scenario_mode=cost_scenario_mode,
    )
    confidence_lines = confidence_narrative(
        frequency_result=frequency_result,
        cost_result=cost_result,
        loss_result=loss_result,
        confidence_level=confidence_level,
    )

    sections = [
        ReportSection(
            title="Simulation Setup",
            bullets=simulation_setup_bullets(
                frequency_scenario_mode=frequency_scenario_mode,
                cost_scenario_mode=cost_scenario_mode,
                scenarios=scenario_items,
            ),
        )
    ]

    frequency_bullets = [_input_source_bullet(frequency_panel_active, frequency_panel_items)]
    if frequency_scenario_mode:
        frequency_bullets.append(
            "Frequency method: Scenario-based sampling from "
            f"{_scenario_count_label(scenario_items)}"
        )
    else:
        frequency_bullets.extend(
            _distribution_bullets(
                frequency_params,
                frequency_distribution,
                use_dollars=False,
            )
        )
    sections.append(ReportSection("Frequency Inputs", tuple(frequency_bullets)))

    cost_bullets = [_input_source_bullet(cost_panel_active, cost_panel_items)]
    if cost_scenario_mode:
        cost_bullets.append(
            f"Cost method: Scenario-based sampling from {_scenario_count_label(scenario_items)}"
        )
    else:
        cost_bullets.extend(_distribution_bullets(cost_params, cost_distribution, use_dollars=True))
    sections.append(ReportSection("Cost Inputs", tuple(cost_bullets)))

    title = "Executive Summary"
    section_tuple = tuple(sections)
    copy_text = _copy_text(title, intro, confidence_lines, section_tuple)
    markdown = _markdown_text(title, intro, confidence_lines, section_tuple)
    return ExecutiveSummary(
        title=title,
        intro=intro,
        confidence_narrative=confidence_lines,
        sections=section_tuple,
        copy_text=copy_text,
        markdown=markdown,
    )


def section_guidance(section: str) -> str:
    """Return plain-language guidance for the Frequency or Cost workflow step."""

    key = str(section).strip().lower()
    try:
        return _SECTION_GUIDANCE[key]
    except KeyError as error:
        raise ValueError("section guidance is only available for 'frequency' and 'cost'") from error


def get_section_description(
    active_section: str,
    **summary_options: object,
) -> PlainDescription | ExecutiveSummary:
    """Return workflow guidance or the Calculate-step executive summary."""

    key = str(active_section).strip().lower()
    if key in _SECTION_GUIDANCE:
        return PlainDescription(section_guidance(key))
    if key == "loss":
        return build_executive_summary(**summary_options)
    raise ValueError("active_section must be 'frequency', 'cost', or 'loss'")
