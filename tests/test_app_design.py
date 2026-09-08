from __future__ import annotations

import ast
import html
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import app as notebook_module
from annual_loss.models import EmpiricalCDF, SimulationResult
from annual_loss.workflow_state import WorkflowModeState


def _qualified_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


@pytest.fixture(scope="module")
def notebook_run() -> tuple[Sequence[Any], Mapping[str, Any]]:
    return notebook_module.app.run()


def test_source_keeps_the_shared_design_system_without_workflow_tabs() -> None:
    source = Path(notebook_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {_qualified_name(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)
    }
    helper_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert "mo.ui.tabs" not in calls
    assert not any("active_workflow_tab" in identifier for identifier in identifiers)
    assert {"surface", "step_header", "panel_heading"} <= helper_names

    for token in (
        "--ald-accent:",
        "--ald-risk-accent:",
        "--ald-rose:",
        "--ald-ink:",
        "--ald-muted:",
        "--ald-border:",
        "--ald-surface:",
        "--ald-surface-soft:",
        ".ald-hero",
        ".ald-shell",
        ".ald-surface",
        ".ald-step-header",
        ".ald-panel-heading",
    ):
        assert token in source

    normalized_source = " ".join(source.split())
    for rule in (
        "--ald-accent: #4f5fbf;",
        "--ald-risk-accent: #B42318;",
        ".ald-eyebrow, .ald-kicker { color: var(--ald-risk-accent);",
        ".ald-hero h1, .ald-step-header h2 { color: var(--ald-ink);",
        ".ald-step-header { border-left: 3px solid var(--ald-risk-accent);",
        ".ald-insight { background: var(--ald-surface-soft); border-left: 3px solid var(--ald-rose);",
    ):
        assert rule in normalized_source

    assert '{"Histogram": "pdf", "CDF": "cdf"}' in source
    assert 'label="Chart view"' in source
    assert 'label="Outcome percentile"' in source
    assert 'label="Central range (%)"' in source
    assert "widths=[0.95, 1.35, 1.75, 1.6]" in source
    assert (
        ".ald-toolbar marimo-radio::part(label), "
        ".ald-toolbar marimo-slider::part(label) { white-space: nowrap;" in normalized_source
    )
    assert 'value="Histogram"' in source
    assert '"PDF / histogram": "pdf"' not in source

    assert ".ald-method-card" not in source
    assert "How the model works" not in source


def test_hero_uses_the_concise_model_introduction(
    notebook_run: tuple[Sequence[Any], Mapping[str, Any]],
) -> None:
    outputs, _ = notebook_run
    hero = next(
        output.text
        for output in outputs
        if hasattr(output, "text") and '<div class="ald-hero">' in output.text
    )
    normalized_hero = " ".join(hero.split())
    introduction = "Estimate the frequency and impact of future breaches in dollar values."

    assert normalized_hero.count(introduction) == 1
    assert "Turn security-risk estimates" not in normalized_hero
    assert "ald-chip" not in normalized_hero
    assert "Local-only" not in normalized_hero
    assert "Seeded simulation" not in normalized_hero
    assert "NumPy + SciPy" not in normalized_hero


def test_rendered_workflow_is_sequential_with_global_view_controls(
    notebook_run: tuple[Sequence[Any], Mapping[str, Any]],
) -> None:
    outputs, definitions = notebook_run
    shells = [
        output.text
        for output in outputs
        if hasattr(output, "text") and '<main class="ald-shell">' in output.text
    ]
    assert len(shells) == 1
    shell = shells[0]

    assert "<marimo-tabs" not in shell
    assert "Annual loss workflow" not in shell

    markers = (
        '<span class="ald-kicker">Step 1</span>',
        "<h2>Frequency</h2>",
        '<span class="ald-kicker">Step 2</span>',
        "<h2>Cost</h2>",
        '<span class="ald-kicker">Step 3</span>',
        "<h2>Calculate annual loss</h2>",
    )
    positions = [shell.find(marker) for marker in markers]
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)

    view_controls_position = shell.index("View controls")
    assert view_controls_position < shell.index("Step 1")

    calculate_html = definitions["calculate_section"].text
    assert "View controls" not in calculate_html
    assert "Configure Frequency and Cost, then calculate the annual-loss distribution." not in shell
    assert "How the model works" not in shell

    main_items = definitions["main_items"]
    assert main_items[0] is definitions["view_controls"]
    section_positions = [
        next(index for index, item in enumerate(main_items) if item is definitions[name])
        for name in ("frequency_section", "cost_section", "calculate_section")
    ]
    assert section_positions == sorted(section_positions)


def test_shared_scenario_editor_precedes_both_scenario_previews() -> None:
    state = [WorkflowModeState(frequency_mode="scenario", cost_mode="scenario")]

    def get_workflow_mode_state() -> WorkflowModeState:
        return state[0]

    def set_workflow_mode_state(value: WorkflowModeState) -> None:
        state[0] = value

    outputs, definitions = notebook_module.app.run(
        defs={
            "get_workflow_mode_state": get_workflow_mode_state,
            "set_workflow_mode_state": set_workflow_mode_state,
        }
    )
    shell = next(
        output.text
        for output in outputs
        if hasattr(output, "text") and '<main class="ald-shell">' in output.text
    )

    model_inputs_position = shell.index("Model inputs")
    scenario_editor_position = shell.index("Shared threat scenarios")
    preview_positions = []
    search_from = 0
    while (position := shell.find("Scenario preview", search_from)) >= 0:
        preview_positions.append(position)
        search_from = position + 1

    assert len(preview_positions) == 2
    assert model_inputs_position < scenario_editor_position < min(preview_positions)
    assert "Shared threat scenarios" in definitions["frequency_section"].text
    assert "Shared threat scenarios" not in definitions["cost_section"].text
    assert shell.count("Shared threat scenarios") == 1


def test_design_refactor_retains_all_dynamic_action_definitions(
    notebook_run: tuple[Sequence[Any], Mapping[str, Any]],
) -> None:
    _, definitions = notebook_run

    scenario_actions = definitions["scenario_actions"]
    assert set(scenario_actions) == {"add", "remove"}
    assert hasattr(scenario_actions["add"], "_update")
    assert isinstance(scenario_actions["remove"], Mapping)

    for section in ("frequency", "cost"):
        panel_actions = definitions[f"{section}_panel_actions"]
        assert set(panel_actions) == {"add", "delete"}
        assert hasattr(panel_actions["add"], "_update")
        assert isinstance(panel_actions["delete"], Mapping)


def test_executive_summary_has_an_adjacent_copy_control_without_report_dialog() -> None:
    frequency_cdf = EmpiricalCDF(
        x=np.asarray([0.0, 5.0, 20.0]),
        probabilities=np.asarray([0.0, 0.5, 1.0]),
    )
    cost_cdf = EmpiricalCDF(
        x=np.asarray([0.0, 100_000.0, 500_000.0]),
        probabilities=np.asarray([0.0, 0.5, 1.0]),
    )
    loss_cdf = EmpiricalCDF(
        x=np.asarray([0.0, 1_000_000.0, 5_000_000.0]),
        probabilities=np.asarray([0.0, 0.5, 1.0]),
    )
    result = SimulationResult(
        samples=np.asarray([0.0, 1_000_000.0, 5_000_000.0]),
        cdf=loss_cdf,
        num_rounds=3,
        seed=12_345,
        total_event_draws=2,
    )
    snapshot = {
        "frequency_params": {"p50": 5.0, "p95": 20.0},
        "cost_params": {"p50": 100_000.0, "p95": 500_000.0},
        "frequency_distribution": "lognormal",
        "cost_distribution": "lognormal",
        "frequency_result": frequency_cdf,
        "cost_result": cost_cdf,
        "scenario_mode": False,
        "scenarios": (),
        "frequency_panel_active": False,
        "cost_panel_active": False,
        "frequency_panelists": (),
        "cost_panelists": (),
    }
    calculation = {"result": result, "snapshot": snapshot, "error": None}

    def get_calculation() -> Mapping[str, Any]:
        return calculation

    def set_calculation(_value: Mapping[str, Any]) -> None:
        return None

    _, definitions = notebook_module.app.run(
        defs={
            "get_calculation": get_calculation,
            "set_calculation": set_calculation,
        }
    )
    calculate_html = definitions["calculate_section"].text

    assert calculate_html.count("<marimo-accordion ") == 1
    assert calculate_html.count("<iframe ") == 1
    assert "Copy or download the report" not in calculate_html
    assert "Read the executive summary" not in calculate_html
    assert "Copy-ready executive report" not in calculate_html
    assert "Download report" not in calculate_html
    assert "<marimo-code-editor " not in calculate_html
    assert "<marimo-download " not in calculate_html

    report_rows = [
        value.text
        for value in definitions.values()
        if hasattr(value, "text")
        and "<marimo-accordion " in value.text
        and "<iframe " in value.text
    ]
    assert report_rows
    report_row = min(report_rows, key=len)
    accordion_position = report_row.index("<marimo-accordion ")
    accordion_tag_end = report_row.index(">", accordion_position)
    iframe_position = report_row.index("<iframe ")

    assert "flex-direction: row" in report_row
    assert "flex: 1" in report_row[:accordion_position]
    assert "Executive Summary" in report_row[accordion_position:accordion_tag_end]
    assert "flex: 0" in report_row[accordion_tag_end:iframe_position]
    assert accordion_position < iframe_position

    source = Path(notebook_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    marker = 'data-testid="copy-executive-summary"'
    marker_line = source[: source.index(marker)].count("\n") + 1
    containing_functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.lineno <= marker_line <= (node.end_lineno or node.lineno)
    ]
    copy_helper = min(
        containing_functions,
        key=lambda node: (node.end_lineno or node.lineno) - node.lineno,
    )
    helper = definitions[copy_helper.name]
    summary = definitions["summary"]
    expected_line = "Simulation mode: Up to 100,000-round distribution-based Monte Carlo"
    embedded_payload = json.dumps(summary.copy_text).replace("<", "\\u003c")
    expected_assignment = f"const reportText = {embedded_payload};"
    copy_control_html = html.unescape(helper(summary.copy_text).text)

    assert expected_line in summary.copy_text
    assert marker in copy_control_html
    assert expected_assignment in copy_control_html
    assert re.search(r">\s*Copy\s*</button>", copy_control_html)
