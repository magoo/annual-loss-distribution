from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from annual_loss.models import DistributionType, EmpiricalCDF, PertParams
from annual_loss.reporting import (
    ExecutiveSummary,
    PlainDescription,
    build_executive_summary,
    confidence_narrative,
    confidence_statement,
    get_section_description,
    section_guidance,
    simulation_setup_bullets,
)


def cdf(values: list[float]) -> EmpiricalCDF:
    return EmpiricalCDF(
        x=np.asarray(values, dtype=np.float64),
        probabilities=np.asarray([0.0, 0.5, 1.0], dtype=np.float64),
    )


def section(summary: ExecutiveSummary, title: str) -> tuple[str, ...]:
    return next(item.bullets for item in summary.sections if item.title == title)


def test_confidence_statement_preserves_chart_summary_wording() -> None:
    statement = confidence_statement(cdf([0, 1_000, 2_000]), section="loss", confidence_level=90)

    assert statement == (
        "The central 90% of modeled annual losses fall between $100 and $1.9K, "
        "with a median of $1K."
    )


def test_confidence_statement_uses_frequency_units_without_currency() -> None:
    statement = confidence_statement(
        cdf([0, 10, 20]),
        section="frequency",
        confidence_level=0.90,
    )

    assert "modeled incidents per year" in statement
    assert "between 1 and 19" in statement
    assert "$" not in statement


def test_confidence_statement_rejects_unknown_section_or_missing_data() -> None:
    with pytest.raises(ValueError, match="section"):
        confidence_statement(cdf([0, 1, 2]), section="unknown")
    with pytest.raises(ValueError, match="non-empty finite"):
        confidence_statement(np.asarray([]), section="loss")


def test_confidence_narrative_covers_frequency_cost_and_loss() -> None:
    narrative = confidence_narrative(
        frequency_result=cdf([0, 10, 20]),
        cost_result=cdf([0, 100_000, 200_000]),
        loss_result=cdf([0, 1_000_000, 2_000_000]),
        confidence_level=90,
    )

    assert narrative == (
        "The central 90% of modeled annual incident counts range between 1 and 19 incidents.",
        "The central 90% of modeled per-incident costs range between $10K and $190K.",
        "The central 90% of modeled annual losses range between $100K and $1.9M.",
    )


def test_default_summary_has_distribution_setup_and_copy_ready_text() -> None:
    summary = build_executive_summary(
        frequency_params={"p50": 6, "p95": 18},
        cost_params={"p50": 120_000, "p95": 700_000},
        frequency_distribution="lognormal",
        cost_distribution=DistributionType.PARETO,
        frequency_result=cdf([0, 10, 20]),
        cost_result=cdf([0, 100_000, 200_000]),
        loss_result=cdf([0, 1_000_000, 2_000_000]),
    )

    assert summary.mode == "executive"
    assert summary.title == "Executive Summary"
    assert "up to 100,000 potential years" in summary.intro
    assert section(summary, "Simulation Setup")[0] == (
        "Simulation mode: Up to 100,000-round distribution-based Monte Carlo"
    )
    assert section(summary, "Frequency Inputs") == (
        "Input source: direct analyst estimate",
        "Distribution: Lognormal",
        "P50 (typical): 6",
        "P95 (high): 18",
    )
    assert "Distribution: Pareto" in section(summary, "Cost Inputs")
    assert "P50 (typical): $120K" in section(summary, "Cost Inputs")
    assert "Modeled Outcome Ranges:" in summary.copy_text
    assert "Simulation Setup:" in summary.copy_text
    assert "### Frequency Inputs" in summary.markdown
    assert summary.as_dict()["mode"] == "executive"


def test_pert_and_panel_inputs_are_described_from_dataclass_like_values() -> None:
    @dataclass
    class Panelist:
        name: str

    summary = build_executive_summary(
        frequency_params=PertParams(min=2, mode=8, max=24),
        cost_params=PertParams(min=25_000, mode=150_000, max=900_000),
        frequency_distribution=DistributionType.PERT,
        cost_distribution=DistributionType.PERT,
        frequency_panelists=[Panelist("Alex"), Panelist("Blair")],
        cost_panelists=[{"name": "Casey"}, {"name": "Devon"}],
    )

    assert section(summary, "Frequency Inputs") == (
        "Input source: panel of 2 experts (Alex, Blair)",
        "Distribution: PERT",
        "Minimum: 2",
        "Most likely: 8",
        "Maximum: 24",
    )
    assert "Input source: panel of 2 experts (Casey, Devon)" in section(summary, "Cost Inputs")
    assert "Minimum: $25K" in section(summary, "Cost Inputs")


def test_scenario_summary_names_scenarios_and_uses_scenario_input_methods() -> None:
    scenarios = (
        {"name": "Ransomware"},
        {"name": " Vendor\n outage "},
    )
    summary = build_executive_summary(
        frequency_scenario_mode=True,
        cost_scenario_mode=True,
        scenarios=(scenario for scenario in scenarios),
    )

    assert "scenario-based Monte Carlo" in summary.intro
    assert section(summary, "Simulation Setup") == (
        "Simulation mode: Up to 10,000-round scenario-based Monte Carlo",
        "Scenario set: 2 threat scenarios (Ransomware, Vendor outage)",
    )
    assert "Frequency method: Scenario-based sampling from 2 threat scenarios" in section(
        summary, "Frequency Inputs"
    )
    assert "Cost method: Scenario-based sampling from 2 threat scenarios" in section(
        summary, "Cost Inputs"
    )


@pytest.mark.parametrize(
    ("frequency_scenarios", "cost_scenarios", "expected_detail"),
    [
        (True, False, "Cost modeling: Distribution-based"),
        (False, True, "Frequency modeling: Distribution-based"),
    ],
)
def test_hybrid_setup_explains_which_side_is_distribution_based(
    frequency_scenarios: bool,
    cost_scenarios: bool,
    expected_detail: str,
) -> None:
    bullets = simulation_setup_bullets(
        frequency_scenario_mode=frequency_scenarios,
        cost_scenario_mode=cost_scenarios,
        scenarios=[{"name": "Credential theft"}],
    )

    assert bullets[0] == "Simulation mode: Up to 10,000-round hybrid Monte Carlo"
    assert expected_detail in bullets


def test_missing_results_are_explicit_instead_of_fabricating_ranges() -> None:
    summary = build_executive_summary()

    assert len(summary.confidence_narrative) == 3
    assert all("n/a and n/a" in statement for statement in summary.confidence_narrative)


def test_confidence_level_accepts_fraction_or_percentage_and_rejects_bounds() -> None:
    percentage = build_executive_summary(confidence_level=90)
    fraction = build_executive_summary(confidence_level=0.9)
    assert percentage.confidence_narrative == fraction.confidence_narrative

    for invalid in (0, 0.49, 1, 49, 96, 100, 101, float("nan")):
        with pytest.raises(ValueError, match="confidence level"):
            build_executive_summary(confidence_level=invalid)


def test_section_descriptions_cover_guidance_and_calculate_modes() -> None:
    frequency = get_section_description("frequency")
    cost = get_section_description("cost")
    loss = get_section_description("loss")

    assert isinstance(frequency, PlainDescription)
    assert "estimate how many incidents" in frequency.text
    assert isinstance(cost, PlainDescription)
    assert "cost of a single incident" in cost.text
    assert isinstance(loss, ExecutiveSummary)
    assert section_guidance("frequency") == frequency.text
    with pytest.raises(ValueError, match="active_section"):
        get_section_description("unknown")
