from __future__ import annotations

import gc
from collections.abc import Callable, Mapping
from typing import Any

import marimo as mo
import pytest
from marimo._plugins.ui._core.ui_element import UIElement

from annual_loss.panel_editor import PanelEditorState
from annual_loss.scenario_editor import ScenarioEditorState
from app import app

PANEL_DEFAULTS = {
    "p50": 10.0,
    "p95": 100.0,
    "min": 1.0,
    "mode": 10.0,
    "max": 100.0,
}


def _run_app(
    defs: dict[str, Any] | None = None,
) -> Mapping[str, Any]:
    _, definitions = app.run(defs=defs)
    return definitions


def _two_panelists() -> PanelEditorState:
    return PanelEditorState.from_rows(
        [
            {"id": 1, "name": "Panelist 1", **PANEL_DEFAULTS},
            {"id": 2, "name": "Panelist 2", **PANEL_DEFAULTS},
        ]
    )


def _panel_state_overrides(
    *,
    frequency: PanelEditorState | None = None,
    cost: PanelEditorState | None = None,
) -> dict[str, Callable[..., Any]]:
    get_frequency, set_frequency = mo.state(frequency or _two_panelists())
    get_cost, set_cost = mo.state(cost or _two_panelists())
    return {
        "get_frequency_panel_state": get_frequency,
        "set_frequency_panel_state": set_frequency,
        "get_cost_panel_state": get_cost,
        "set_cost_panel_state": set_cost,
    }


def _click(button: UIElement[Any, Any]) -> None:
    gc.collect()
    button._update(1)


def _scenario_state_overrides(
    state: ScenarioEditorState,
) -> dict[str, Callable[..., Any]]:
    get_scenario, set_scenario = mo.state(state)
    return {
        "get_scenario_editor_state": get_scenario,
        "set_scenario_editor_state": set_scenario,
    }


def test_all_initial_scenario_remove_controls_are_retained() -> None:
    definitions = _run_app()
    state = definitions["get_scenario_editor_state"]()
    actions = definitions["scenario_actions"]

    assert isinstance(actions["add"], UIElement)
    assert set(actions["remove"]) == {row.id for row in state.rows}
    assert all(isinstance(button, UIElement) for button in actions["remove"].values())


def test_retained_scenario_remove_control_removes_a_non_final_row_after_gc() -> None:
    definitions = _run_app()
    get_state = definitions["get_scenario_editor_state"]
    initial_ids = [row.id for row in get_state().rows]
    removed_id = initial_ids[0]

    _click(definitions["scenario_actions"]["remove"][removed_id])

    assert [row.id for row in get_state().rows] == initial_ids[1:]


def test_retained_scenario_add_control_adds_a_row_after_gc() -> None:
    definitions = _run_app()
    get_state = definitions["get_scenario_editor_state"]
    initial_state = get_state()

    _click(definitions["scenario_actions"]["add"])

    updated = get_state()
    assert len(updated.rows) == len(initial_state.rows) + 1
    assert [row.id for row in updated.rows[:-1]] == [row.id for row in initial_state.rows]
    assert updated.rows[-1].id == initial_state.next_id


def test_single_scenario_renders_no_remove_action_or_remove_text() -> None:
    one_scenario = ScenarioEditorState.from_rows([{"id": 1, "name": "Only scenario"}])
    definitions = _run_app(defs=_scenario_state_overrides(one_scenario))

    assert definitions["scenario_actions"]["remove"] == {}
    assert ">Remove<" not in definitions["scenario_section"].text


@pytest.mark.parametrize("section", ["frequency", "cost"])
def test_each_retained_panel_add_control_grows_only_its_panel_after_gc(section: str) -> None:
    definitions = _run_app()
    get_selected = definitions[f"get_{section}_panel_state"]
    other_section = "cost" if section == "frequency" else "frequency"
    get_other = definitions[f"get_{other_section}_panel_state"]

    assert len(get_selected().rows) == len(get_other().rows) == 2
    _click(definitions[f"{section}_panel_actions"]["add"])

    assert len(get_selected().rows) == 3
    assert len(get_other().rows) == 2


def test_initial_two_member_panels_render_no_delete_actions_or_delete_text() -> None:
    definitions = _run_app()

    for section in ("frequency", "cost"):
        actions = definitions[f"{section}_panel_actions"]
        rendered_panel = definitions[f"{section}_panel"]
        assert isinstance(actions["add"], UIElement)
        assert actions["delete"] == {}
        assert "Delete panelist" not in rendered_panel.text


@pytest.mark.parametrize("section", ["frequency", "cost"])
def test_three_member_panels_retain_every_delete_and_can_return_to_two(section: str) -> None:
    three_panelists = _two_panelists().add_panelist(PANEL_DEFAULTS)
    overrides = _panel_state_overrides(**{section: three_panelists})
    definitions = _run_app(defs=overrides)
    get_state = definitions[f"get_{section}_panel_state"]
    actions = definitions[f"{section}_panel_actions"]
    initial_ids = [row.id for row in get_state().rows]

    assert set(actions["delete"]) == set(initial_ids)
    assert all(isinstance(button, UIElement) for button in actions["delete"].values())

    removed_id = initial_ids[0]
    _click(actions["delete"][removed_id])

    assert [row.id for row in get_state().rows] == initial_ids[1:]
    assert len(get_state().rows) == 2
