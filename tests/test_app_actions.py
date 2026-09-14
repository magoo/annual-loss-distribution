"""Persistent editor actions retain identities and all values in portable snapshots.

Actual DOM actions are exercised by browser_tests/test_analysis_workspace.py.
These tests cover the model state that those actions must preserve.
"""

from annual_loss.analysis_document import make_document, parse_backup, serialize_backup
from annual_loss.panel_editor import PanelEditorRow, PanelEditorState
from annual_loss.scenario_editor import ScenarioEditorRow, ScenarioEditorState


def test_panel_add_delete_after_reopen_preserves_edits_and_never_reuses_ids():
    doc = make_document()
    doc["frequency"]["panel"]["rows"][0]["name"] = "Edited expert"
    source = parse_backup(serialize_backup([doc]))[0]["frequency"]["panel"]
    state = PanelEditorState(
        tuple(PanelEditorRow(**row) for row in source["rows"]), source["next_id"]
    )
    added = state.add_panelist(source["rows"][0], name="Another expert")
    removed_id = added.rows[-1].id
    reduced = added.remove_panelist(removed_id)
    assert reduced.rows[0].name == "Edited expert"
    assert len(reduced.rows) == 2
    assert reduced.remove_panelist(reduced.rows[0].id) == reduced
    assert reduced.add_panelist(source["rows"][0]).rows[-1].id > removed_id


def test_scenario_add_remove_after_reopen_preserves_hidden_values():
    doc = make_document()
    doc["scenarios"]["rows"][0]["frequency_p95"] = 71
    source = parse_backup(serialize_backup([doc]))[0]["scenarios"]
    state = ScenarioEditorState(
        tuple(ScenarioEditorRow(**row) for row in source["rows"]), source["next_id"]
    )
    added = state.add_scenario()
    assert added.rows[0].frequency_p95 == 71
    reduced = added.remove_scenario(added.rows[-1].id)
    assert reduced.rows == state.rows
    assert reduced.next_id > state.next_id
    single = ScenarioEditorState((reduced.rows[0],), reduced.next_id)
    assert single.remove_scenario(single.rows[0].id) == single
