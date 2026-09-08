from dataclasses import FrozenInstanceError

import pytest

from annual_loss.models import DistributionType, FrequencyMethod, Scenario
from annual_loss.scenario_editor import (
    ScenarioEditorRow,
    ScenarioEditorState,
    cost_parameter_fields,
    frequency_parameter_fields,
)
from annual_loss.validation import validate_params


def sample_rows() -> list[dict[str, object]]:
    return [
        {
            "id": 1,
            "name": "Product exploit",
            "frequency_method": "odds",
            "frequency_odds": 3,
            "cost_dist_type": "lognormal",
            "cost_p50": 100_000,
            "cost_p95": 1_000_000,
        },
        {
            "id": 2,
            "name": "Insider",
            "frequency_method": "pert",
            "frequency_min": 0,
            "frequency_mode": 1,
            "frequency_max": 5,
            "cost_dist_type": "pareto",
            "cost_p50": 200_000,
            "cost_p95": 2_000_000,
        },
    ]


def test_initialization_normalizes_flat_rows_and_all_hidden_slots() -> None:
    source = sample_rows()
    state = ScenarioEditorState.from_rows(source)

    assert isinstance(state.rows, tuple)
    assert [row.id for row in state.rows] == [1, 2]
    assert state.next_id == 3
    assert state.to_rows()[0] == {
        "id": 1,
        "name": "Product exploit",
        "frequency_method": "odds",
        "frequency_odds": 3,
        "frequency_p50": 1.0,
        "frequency_p95": 10.0,
        "frequency_min": 0.0,
        "frequency_mode": 1.0,
        "frequency_max": 10.0,
        "cost_dist_type": "lognormal",
        "cost_p50": 100_000,
        "cost_p95": 1_000_000,
        "cost_min": 1_000.0,
        "cost_mode": 50_000.0,
        "cost_max": 500_000.0,
    }
    assert "frequency_p50" not in source[0]


def test_initialization_accepts_enums_and_assigns_missing_ids_safely() -> None:
    state = ScenarioEditorState.from_rows(
        [
            {
                "name": "Needs id",
                "frequency_method": FrequencyMethod.LOGNORMAL,
                "cost_dist_type": DistributionType.PERT,
            },
            {"id": 7, "name": "Existing id"},
            {"name": "Also needs id"},
        ]
    )

    assert [row.id for row in state.rows] == [8, 7, 9]
    assert state.rows[0].frequency_method == "lognormal"
    assert state.rows[0].cost_dist_type == "pert"
    assert state.next_id == 10


def test_initialization_rejects_empty_duplicate_or_unknown_method_rows() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ScenarioEditorState.from_rows([])
    with pytest.raises(ValueError, match="unique"):
        ScenarioEditorState.from_rows([{"id": 1}, {"id": 1}])
    with pytest.raises(ValueError, match="frequency method"):
        ScenarioEditorState.from_rows([{"id": 1, "frequency_method": "uniform"}])
    with pytest.raises(TypeError, match="mappings"):
        ScenarioEditorState.from_rows([object()])  # type: ignore[list-item]


def test_state_and_rows_are_frozen_and_exports_are_independent_mutable_copies() -> None:
    state = ScenarioEditorState.from_rows(sample_rows())

    with pytest.raises(FrozenInstanceError):
        state.next_id = 20  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.rows[0].name = "Changed"  # type: ignore[misc]

    exported = state.to_rows()
    exported[0]["name"] = "Changed outside state"
    assert state.rows[0].name == "Product exploit"


def test_with_rows_synchronizes_values_immutably_and_preserves_next_id() -> None:
    state = ScenarioEditorState.from_rows([{"id": 1}, {"id": 5}])
    rows = state.to_rows()
    rows[0]["name"] = "Renamed"
    rows[0]["frequency_p50"] = 42
    rows[1]["cost_p50"] = 765_432
    synchronized = state.with_rows(rows)

    assert state.rows[0].name == "Scenario 1"
    assert synchronized.rows[0].name == "Renamed"
    assert synchronized.rows[0].frequency_p50 == 42
    assert synchronized.rows[1].cost_p50 == 765_432
    assert synchronized.next_id == state.next_id == 6
    assert synchronized.with_rows(synchronized.to_rows()) is synchronized


def test_with_rows_merges_partial_rows_to_preserve_hidden_parameter_values() -> None:
    state = ScenarioEditorState.from_rows(
        [
            {
                "id": 1,
                "frequency_method": "lognormal",
                "frequency_p50": 77,
                "frequency_p95": 900,
                "frequency_min": 4,
                "frequency_mode": 8,
                "frequency_max": 40,
                "cost_dist_type": "lognormal",
                "cost_p50": 888_888,
                "cost_p95": 9_000_000,
                "cost_min": 12_000,
                "cost_mode": 123_456,
                "cost_max": 2_000_000,
            }
        ]
    )

    pert = state.with_rows([{"id": 1, "frequency_method": "pert", "cost_dist_type": "pert"}])
    assert pert.rows[0].frequency_method == "pert"
    assert pert.rows[0].frequency_p50 == 77
    assert pert.rows[0].frequency_min == 4
    assert pert.rows[0].cost_dist_type == "pert"
    assert pert.rows[0].cost_p50 == 888_888
    assert pert.rows[0].cost_mode == 123_456

    restored = pert.with_rows(
        [{"id": 1, "frequency_method": "lognormal", "cost_dist_type": "lognormal"}]
    )
    assert restored.rows[0].frequency_p50 == 77
    assert restored.rows[0].cost_p50 == 888_888


@pytest.mark.parametrize(
    "invalid_rows",
    [
        [{"id": 1}],
        [{"id": 1}, {"id": 2}, {"id": 3}],
        [{"id": 2}, {"id": 1}],
        [{"id": 1}, {"id": 99}],
    ],
)
def test_with_rows_rejects_removed_added_reordered_or_changed_ids(invalid_rows) -> None:
    state = ScenarioEditorState.from_rows([{"id": 1}, {"id": 2}])

    with pytest.raises(ValueError, match="same stable ids.*same order"):
        state.with_rows(invalid_rows)


def test_with_rows_requires_every_stable_id_and_valid_methods() -> None:
    state = ScenarioEditorState.from_rows([{"id": 1}])

    with pytest.raises(ValueError, match="include stable ids"):
        state.with_rows([{"name": "Missing id"}])
    with pytest.raises(ValueError, match="cost distribution"):
        state.with_rows([{"id": 1, "cost_dist_type": "odds"}])


def test_add_appends_a_complete_safe_default_without_changing_existing_rows() -> None:
    state = ScenarioEditorState.from_rows([{"id": 1, "name": "One"}, {"id": 4, "name": "Four"}])
    added = state.add_scenario()

    assert [row.id for row in state.rows] == [1, 4]
    assert [row.id for row in added.rows] == [1, 4, 5]
    assert added.next_id == 6
    assert added.rows[-1].to_flat_row() == {
        "id": 5,
        "name": "New scenario 5",
        "frequency_method": "odds",
        "frequency_odds": 10.0,
        "frequency_p50": 1.0,
        "frequency_p95": 10.0,
        "frequency_min": 0.0,
        "frequency_mode": 1.0,
        "frequency_max": 10.0,
        "cost_dist_type": "lognormal",
        "cost_p50": 50_000.0,
        "cost_p95": 500_000.0,
        "cost_min": 1_000.0,
        "cost_mode": 50_000.0,
        "cost_max": 500_000.0,
    }


def test_sync_before_add_preserves_current_widget_values() -> None:
    state = ScenarioEditorState.from_rows(sample_rows())
    rows = state.to_rows()
    rows[0]["frequency_odds"] = 17
    rows[1]["name"] = "Edited insider"

    added = state.with_rows(rows).add_scenario()

    assert added.rows[0].frequency_odds == 17
    assert added.rows[1].name == "Edited insider"
    assert added.rows[-1].name == "New scenario 3"


@pytest.mark.parametrize(
    ("removed_id", "expected_ids"),
    [(1, [2, 3]), (2, [1, 3]), (3, [1, 2])],
)
def test_remove_targets_a_stable_id_without_reordering_survivors(removed_id, expected_ids) -> None:
    state = ScenarioEditorState.from_rows([{"id": 1}, {"id": 2}, {"id": 3}])

    removed = state.remove_scenario(removed_id)

    assert [row.id for row in removed.rows] == expected_ids
    assert removed.next_id == state.next_id == 4


def test_sync_before_remove_preserves_edits_on_surviving_rows() -> None:
    state = ScenarioEditorState.from_rows(sample_rows())
    rows = state.to_rows()
    rows[0]["name"] = "Edited product exploit"
    rows[0]["cost_p50"] = 333_333

    removed = state.with_rows(rows).remove_scenario(2)

    assert len(removed.rows) == 1
    assert removed.rows[0].name == "Edited product exploit"
    assert removed.rows[0].cost_p50 == 333_333


def test_remove_guards_the_final_row_and_rejects_unknown_ids() -> None:
    state = ScenarioEditorState.from_rows([{"id": 1, "name": "Only"}])

    assert state.remove_scenario(1) is state
    with pytest.raises(KeyError, match="unknown scenario id"):
        state.remove_scenario(99)


def test_removed_ids_are_not_reused_during_the_same_state_history() -> None:
    state = ScenarioEditorState.from_rows([{"id": 1}, {"id": 5}])
    state = state.add_scenario()  # ID 6, next ID 7.
    state = state.remove_scenario(6)
    state = state.add_scenario()

    assert [row.id for row in state.rows] == [1, 5, 7]
    assert state.rows[-1].name == "New scenario 7"
    assert state.next_id == 8


def test_rows_bridge_directly_to_scenario_models_and_validation() -> None:
    state = ScenarioEditorState.from_rows(
        [
            {
                "id": 1,
                "name": "PERT threat",
                "frequency_method": "pert",
                "frequency_min": 0,
                "frequency_mode": 2,
                "frequency_max": 8,
                "cost_dist_type": "pareto",
                "cost_p50": 25_000,
                "cost_p95": 250_000,
            }
        ]
    ).add_scenario()

    scenarios = [Scenario.from_dict(row) for row in state.to_rows()]
    assert {key: scenarios[0].frequency_params[key] for key in ("min", "mode", "max")} == {
        "min": 0,
        "mode": 2,
        "max": 8,
    }
    assert {key: scenarios[0].cost_params[key] for key in ("p50", "p95")} == {
        "p50": 25_000,
        "p95": 250_000,
    }
    for scenario in scenarios:
        assert (
            validate_params("frequency", scenario.frequency_method, scenario.frequency_params) == {}
        )
        assert validate_params("cost", scenario.cost_dist_type, scenario.cost_params) == {}


def test_parameter_field_helpers_return_unprefixed_method_specific_names() -> None:
    assert frequency_parameter_fields("odds") == ("odds",)
    assert frequency_parameter_fields(FrequencyMethod.LOGNORMAL) == ("p50", "p95")
    assert frequency_parameter_fields("pareto") == ("p50", "p95")
    assert frequency_parameter_fields("pert") == ("min", "mode", "max")
    assert cost_parameter_fields(DistributionType.LOGNORMAL) == ("p50", "p95")
    assert cost_parameter_fields("pareto") == ("p50", "p95")
    assert cost_parameter_fields("pert") == ("min", "mode", "max")


def test_state_accepts_already_normalized_rows() -> None:
    row = ScenarioEditorRow.from_flat_row({"id": "a", "name": "A"})
    state = ScenarioEditorState.from_rows([row])

    assert state.rows[0] is row
