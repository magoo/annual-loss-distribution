from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from annual_loss.models import Section
from annual_loss.workflow_state import WorkflowModeState


def test_default_state_is_independent_direct_mode() -> None:
    state = WorkflowModeState()

    assert state.frequency_mode == "direct"
    assert state.cost_mode == "direct"
    assert state.remembered_frequency_mode == "direct"
    assert state.remembered_cost_mode == "direct"
    assert state.frequency_non_scenario_mode == "direct"
    assert state.cost_non_scenario_mode == "direct"
    assert state.scenario_mode is False


def test_non_scenario_constructor_infers_matching_memories() -> None:
    state = WorkflowModeState(frequency_mode="panel", cost_mode="direct")

    assert state.remembered_frequency_mode == "panel"
    assert state.remembered_cost_mode == "direct"


def test_selecting_scenario_from_either_section_links_both_modes() -> None:
    independent = WorkflowModeState(frequency_mode="panel", cost_mode="direct")

    from_frequency = independent.select("frequency", "scenario")
    from_cost = independent.select("cost", "scenario")

    assert from_frequency == from_cost
    assert from_frequency.frequency_mode == from_frequency.cost_mode == "scenario"
    assert from_frequency.remembered_frequency_mode == "panel"
    assert from_frequency.remembered_cost_mode == "direct"
    assert from_frequency.scenario_mode is True
    assert from_frequency.select("frequency", "scenario") is from_frequency


@pytest.mark.parametrize(
    ("section", "mode", "expected_frequency", "expected_cost"),
    [
        ("frequency", "direct", "direct", "panel"),
        ("frequency", "panel", "panel", "panel"),
        ("cost", "direct", "direct", "direct"),
        ("cost", "panel", "direct", "panel"),
    ],
)
def test_non_scenario_selection_while_linked_exits_and_restores_other_memory(
    section,
    mode,
    expected_frequency,
    expected_cost,
) -> None:
    linked = WorkflowModeState(
        frequency_mode="scenario",
        cost_mode="scenario",
        remembered_frequency_mode="direct",
        remembered_cost_mode="panel",
    )

    restored = linked.select(section, mode)

    assert restored.frequency_mode == expected_frequency
    assert restored.cost_mode == expected_cost
    assert restored.scenario_mode is False
    assert restored.remembered_frequency_mode == expected_frequency
    assert restored.remembered_cost_mode == expected_cost


def test_ordinary_changes_affect_only_the_selected_section_and_update_memory() -> None:
    initial = WorkflowModeState()
    frequency_panel = initial.select("frequency", "panel")
    both_panel = frequency_panel.select(Section.COST, "panel")
    frequency_direct = both_panel.select(Section.FREQUENCY, "direct")

    assert (frequency_panel.frequency_mode, frequency_panel.cost_mode) == ("panel", "direct")
    assert (both_panel.frequency_mode, both_panel.cost_mode) == ("panel", "panel")
    assert (frequency_direct.frequency_mode, frequency_direct.cost_mode) == (
        "direct",
        "panel",
    )
    assert frequency_direct.remembered_frequency_mode == "direct"
    assert frequency_direct.remembered_cost_mode == "panel"
    assert initial.select("frequency", "direct") is initial


def test_round_trip_restores_latest_independent_modes_after_repeated_linking() -> None:
    state = WorkflowModeState()
    state = state.select("cost", "panel")
    state = state.select("frequency", "scenario")
    state = state.select("frequency", "panel")
    state = state.select("cost", "direct")
    state = state.select("cost", "scenario")
    state = state.select("cost", "panel")

    assert (state.frequency_mode, state.cost_mode) == ("panel", "panel")
    assert state.remembered_frequency_mode == "panel"
    assert state.remembered_cost_mode == "panel"


def test_state_is_frozen_and_transitions_leave_prior_state_unchanged() -> None:
    state = WorkflowModeState()
    changed = state.select("frequency", "panel")

    with pytest.raises(FrozenInstanceError):
        state.frequency_mode = "panel"  # type: ignore[misc]
    assert state.frequency_mode == "direct"
    assert changed.frequency_mode == "panel"


@pytest.mark.parametrize("section", ["loss", "Frequency", "", 1, None])
def test_select_rejects_invalid_sections(section) -> None:
    error = TypeError if not isinstance(section, str) else ValueError
    with pytest.raises(error, match="section"):
        WorkflowModeState().select(section, "direct")


@pytest.mark.parametrize("mode", ["hybrid", "Direct", "", 1, None])
def test_select_rejects_invalid_modes(mode) -> None:
    error = TypeError if not isinstance(mode, str) else ValueError
    with pytest.raises(error, match="mode"):
        WorkflowModeState().select("frequency", mode)


def test_constructor_rejects_half_linked_scenario_state() -> None:
    with pytest.raises(ValueError, match="together"):
        WorkflowModeState(frequency_mode="scenario", cost_mode="direct")
    with pytest.raises(ValueError, match="together"):
        WorkflowModeState(frequency_mode="panel", cost_mode="scenario")


def test_constructor_rejects_invalid_or_inconsistent_memories() -> None:
    with pytest.raises(ValueError, match="remembered_frequency_mode"):
        WorkflowModeState(
            frequency_mode="scenario",
            cost_mode="scenario",
            remembered_frequency_mode="scenario",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="match"):
        WorkflowModeState(
            frequency_mode="panel",
            remembered_frequency_mode="direct",
        )
    with pytest.raises(TypeError, match="remembered_cost_mode"):
        WorkflowModeState(remembered_cost_mode=1)  # type: ignore[arg-type]


def test_linked_constructor_defaults_both_memories_to_direct() -> None:
    state = WorkflowModeState(frequency_mode="scenario", cost_mode="scenario")

    assert state.scenario_mode
    assert state.frequency_non_scenario_mode == "direct"
    assert state.cost_non_scenario_mode == "direct"
