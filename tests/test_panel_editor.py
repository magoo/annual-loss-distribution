from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from annual_loss.panel_editor import PanelEditorRow, PanelEditorState


def defaults(offset: int = 0) -> dict[str, object]:
    return {
        "p50": 10 + offset,
        "p95": 95 + offset,
        "min": 1 + offset,
        "mode": 5 + offset,
        "max": 100 + offset,
    }


def initial_rows() -> list[dict[str, object]]:
    return [
        {"id": 1, "name": "Alex", **defaults()},
        {"id": 4, "name": "Blair", **defaults(100)},
    ]


def test_from_rows_normalizes_order_fields_and_next_id_without_mutating_input() -> None:
    source = [
        {"id": 2, "name": "Alex", "p50": "still editing"},
        {"id": 8, "name": "Blair", "min": None},
    ]

    state = PanelEditorState.from_rows(source)

    assert isinstance(state.rows, tuple)
    assert [row.id for row in state.rows] == [2, 8]
    assert state.next_id == 9
    assert state.to_rows()[0] == {
        "id": 2,
        "name": "Alex",
        "p50": "still editing",
        "p95": None,
        "min": None,
        "mode": None,
        "max": None,
    }
    assert "p95" not in source[0]


def test_from_rows_assigns_missing_ids_above_all_supplied_ids() -> None:
    state = PanelEditorState.from_rows(
        [
            {"name": "Needs ID"},
            {"id": 10, "name": "Existing"},
            {"name": "Also needs ID"},
        ]
    )

    assert [row.id for row in state.rows] == [11, 10, 12]
    assert state.next_id == 13


def test_from_rows_accepts_normalized_rows_and_generators() -> None:
    first = PanelEditorRow.from_flat_row({"id": 1, "name": "First"})
    second = PanelEditorRow.from_flat_row({"id": 2, "name": "Second"})

    state = PanelEditorState.from_rows(row for row in (first, second))

    assert state.rows == (first, second)
    assert state.rows[0] is first


@pytest.mark.parametrize("rows", [[], [{"id": 1}]])
def test_from_rows_enforces_a_hard_two_panelist_minimum(rows) -> None:
    with pytest.raises(ValueError, match="at least two"):
        PanelEditorState.from_rows(rows)


def test_from_rows_rejects_duplicate_invalid_ids_and_non_rows() -> None:
    with pytest.raises(ValueError, match="unique"):
        PanelEditorState.from_rows([{"id": 1}, {"id": 1}])
    with pytest.raises(ValueError, match="positive integers"):
        PanelEditorState.from_rows([{"id": 0}, {"id": 2}])
    with pytest.raises(ValueError, match="positive integers"):
        PanelEditorState.from_rows([{"id": True}, {"id": 2}])
    with pytest.raises(TypeError, match="mappings"):
        PanelEditorState.from_rows([object(), object()])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="iterable"):
        PanelEditorState.from_rows({"id": 1})  # type: ignore[arg-type]


def test_rows_and_state_are_frozen_and_exports_are_fresh_mappings() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    with pytest.raises(FrozenInstanceError):
        state.next_id = 99  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.rows[0].name = "Changed"  # type: ignore[misc]

    exported = state.to_rows()
    exported[0]["name"] = "Changed elsewhere"
    assert state.rows[0].name == "Alex"


def test_with_rows_updates_values_immutably_and_preserves_next_id() -> None:
    state = PanelEditorState.from_rows(initial_rows())
    edited = state.to_rows()
    edited[0]["name"] = "Alexandra"
    edited[1]["p50"] = "unfinished"

    synchronized = state.with_rows(edited)

    assert state.rows[0].name == "Alex"
    assert synchronized.rows[0].name == "Alexandra"
    assert synchronized.rows[1].p50 == "unfinished"
    assert synchronized.next_id == state.next_id == 5
    assert synchronized.with_rows(synchronized.to_rows()) is synchronized


def test_with_rows_preserves_fields_hidden_by_the_current_distribution() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    pert_visible = state.with_rows(
        [
            {"id": 1, "name": "Alex", "min": 3, "mode": 8, "max": 21},
            {"id": 4, "name": "Blair", "min": 4, "mode": 9, "max": 22},
        ]
    )
    p50_visible_again = pert_visible.with_rows(
        [
            {"id": 1, "name": "Alex", "p50": 44, "p95": 444},
            {"id": 4, "name": "Blair", "p50": 55, "p95": 555},
        ]
    )

    assert pert_visible.rows[0].p50 == 10
    assert pert_visible.rows[1].p95 == 195
    assert p50_visible_again.rows[0].min == 3
    assert p50_visible_again.rows[0].mode == 8
    assert p50_visible_again.rows[0].max == 21


@pytest.mark.parametrize(
    "rows",
    [
        [{"id": 1}],
        [{"id": 1}, {"id": 4}, {"id": 5}],
        [{"id": 4}, {"id": 1}],
        [{"id": 1}, {"id": 99}],
    ],
)
def test_with_rows_rejects_removed_added_reordered_or_changed_ids(rows) -> None:
    state = PanelEditorState.from_rows(initial_rows())

    with pytest.raises(ValueError, match="same stable ids.*same order"):
        state.with_rows(rows)


def test_with_rows_requires_ids_mappings_and_valid_names() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    with pytest.raises(ValueError, match="include stable ids"):
        state.with_rows([{"name": "Missing"}, {"id": 4}])
    with pytest.raises(TypeError, match="mappings"):
        state.with_rows([state.rows[0], object()])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="name"):
        state.with_rows([{"id": 1, "name": 123}, {"id": 4}])


def test_add_panelist_uses_full_defaults_and_optional_name() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    generated = state.add_panelist(defaults(200))
    named = generated.add_panelist({**defaults(300), "name": "Casey"})
    overridden = named.add_panelist({**defaults(400), "name": "Ignored"}, name="Devon")

    assert [row.id for row in generated.rows] == [1, 4, 5]
    assert generated.rows[-1].to_flat_row() == {
        "id": 5,
        "name": "Panelist 5",
        **defaults(200),
    }
    assert named.rows[-1].name == "Casey"
    assert overridden.rows[-1].name == "Devon"
    assert overridden.next_id == 8


def test_add_panelist_requires_a_full_mapping_and_string_name() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    with pytest.raises(TypeError, match="mapping"):
        state.add_panelist(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="missing: p95, min, mode, max"):
        state.add_panelist({"p50": 1})
    with pytest.raises(TypeError, match="name"):
        state.add_panelist(defaults(), name=123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("removed_id", "remaining"),
    [(1, [4, 5]), (4, [1, 5]), (5, [1, 4])],
)
def test_remove_panelist_targets_stable_id_without_reordering(removed_id, remaining) -> None:
    state = PanelEditorState.from_rows(initial_rows()).add_panelist(defaults(200))

    removed = state.remove_panelist(removed_id)

    assert [row.id for row in removed.rows] == remaining
    assert removed.next_id == state.next_id == 6


def test_remove_panelist_guards_two_member_floor_and_rejects_unknown_id() -> None:
    state = PanelEditorState.from_rows(initial_rows())

    assert state.remove_panelist(1) is state
    with pytest.raises(KeyError, match="unknown panelist id"):
        state.remove_panelist(99)


def test_removed_ids_are_never_reused_within_a_state_history() -> None:
    state = PanelEditorState.from_rows(initial_rows())
    state = state.add_panelist(defaults(200))  # ID 5, next ID 6.
    state = state.remove_panelist(5)
    state = state.add_panelist(defaults(300))

    assert [row.id for row in state.rows] == [1, 4, 6]
    assert state.next_id == 7


def test_sync_before_structural_changes_preserves_current_widget_edits() -> None:
    state = PanelEditorState.from_rows(initial_rows()).add_panelist(defaults(200))
    rows = state.to_rows()
    rows[0]["name"] = "Edited Alex"
    rows[0]["p95"] = 999

    changed = state.with_rows(rows).remove_panelist(4).add_panelist(defaults(300))

    assert changed.rows[0].name == "Edited Alex"
    assert changed.rows[0].p95 == 999
    assert [row.id for row in changed.rows] == [1, 5, 6]


def test_direct_state_construction_validates_next_id_monotonicity() -> None:
    rows = PanelEditorState.from_rows(initial_rows()).rows

    with pytest.raises(ValueError, match="greater than every"):
        PanelEditorState(rows=rows, next_id=4)
    state = PanelEditorState(rows=rows, next_id=100)
    assert state.add_panelist(defaults()).rows[-1].id == 100
