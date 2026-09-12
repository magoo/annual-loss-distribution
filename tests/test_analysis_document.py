"""Portable backups must preserve unfinished work without admitting unsafe shapes."""

import json
from copy import deepcopy

import pytest

from annual_loss.analysis_document import (
    FIELDS,
    FORMAT,
    LIBRARY_FORMAT,
    MAX_BACKUP_BYTES,
    active_fields,
    editable_fields,
    make_document,
    parse_backup,
    serialize_backup,
    validate_document,
)
from annual_loss.panel_editor import PanelEditorState
from annual_loss.scenario_editor import ScenarioEditorState
from annual_loss.workflow_state import WorkflowModeState


def test_complete_defaults_and_stable_readable_backup():
    doc = make_document()
    before = deepcopy(doc)
    text = serialize_backup([doc])
    assert text.endswith("\n") and '\n  "' in text
    assert parse_backup(text) == [doc] == parse_backup(text.encode())
    assert parse_backup("\ufeff" + text) == [doc]
    assert doc == before
    assert serialize_backup([doc]) == text
    assert doc["format"] == FORMAT
    assert all(set(row) >= set(FIELDS) for row in doc["frequency"]["panel"]["rows"])
    assert doc["scenarios"]["next_id"] > max(row["id"] for row in doc["scenarios"]["rows"])
    assert "loss" not in doc and "results" not in doc


def test_all_modes_hidden_values_raw_drafts_and_row_ids_round_trip():
    doc = make_document("社内 risk analysis")
    doc["frequency"]["direct"]["pareto"]["p50"] = 42
    doc["frequency"]["panel"]["rows"][0]["name"] = "Expert <script>alert(1)</script>"
    doc["cost"]["panel"]["rows"][1]["min"] = -1
    doc["scenarios"]["rows"][0]["frequency_p95"] = 34
    doc["scenarios"]["next_id"] = 100
    doc["workflow"] = {
        "frequency_mode": "scenario",
        "cost_mode": "scenario",
        "remembered_frequency_mode": "panel",
        "remembered_cost_mode": "direct",
    }
    doc["drafts"] = {
        path: "1e" if numeric else "Unfinished name"
        for path, (_, _, numeric) in editable_fields(doc).items()
    }
    assert parse_backup(serialize_backup([doc])) == [doc]
    state = WorkflowModeState(**doc["workflow"]).select("cost", "direct")
    assert state.frequency_mode == "panel"
    assert "\\u793e" not in serialize_backup([doc])


def test_panel_and_scenario_identity_allocation_survives_round_trip():
    doc = make_document()
    panel = PanelEditorState.from_rows(doc["frequency"]["panel"]["rows"])
    panel = panel.add_panelist(panel.rows[0].to_flat_row())
    removed = panel.rows[-1].id
    panel = panel.remove_panelist(removed)
    doc["frequency"]["panel"] = {"rows": panel.to_rows(), "next_id": panel.next_id}
    scenarios = ScenarioEditorState.from_rows(doc["scenarios"]["rows"]).add_scenario()
    removed_scenario = scenarios.rows[-1].id
    scenarios = scenarios.remove_scenario(removed_scenario)
    doc["scenarios"] = {"rows": scenarios.to_rows(), "next_id": scenarios.next_id}
    restored = parse_backup(serialize_backup([doc]))[0]
    assert restored["frequency"]["panel"]["next_id"] > removed
    assert restored["scenarios"]["next_id"] > removed_scenario


def test_valid_unfinished_and_invalid_model_values_are_recoverable():
    doc = make_document()
    doc["frequency"]["direct"]["lognormal"] = {"p50": -4, "p95": -5}
    doc["drafts"] = {"seed": "-", "cost:direct:pert:min": "", "scenario:integer:1:name": ""}
    assert validate_document(doc) is doc
    assert parse_backup(serialize_backup([doc])) == [doc]
    assert "cost:direct:pert:min" not in active_fields(doc)
    assert "seed" in active_fields(doc)


def test_library_ordering_does_not_reorder_model_rows():
    first, second = make_document("A"), make_document("B")
    first["scenarios"]["rows"].reverse()
    data = json.loads(serialize_backup([second, first], library=True))
    assert data["format"] == LIBRARY_FORMAT
    assert [d["id"] for d in data["analyses"]] == sorted([first["id"], second["id"]])
    assert (
        next(d for d in data["analyses"] if d["id"] == first["id"])["scenarios"]["rows"]
        == first["scenarios"]["rows"]
    )


INVALID_CHANGES = [
    ("format", "security-budget"),
    ("version", 99),
    ("version", True),
    ("model_version", 2),
    ("id", "../escape"),
    ("name", ""),
    ("created_at", "2026-02-30T00:00:00.000Z"),
    ("updated_at", "yesterday"),
    ("seed", 1.5),
    ("seed", True),
    ("seed", -1),
    ("seed", 2**53),
    ("view.chart", "scatter"),
    ("view.focus_percentile", 100),
    ("view.confidence_level", 50.1),
    ("workflow.cost_mode", "scenario"),
    ("workflow.remembered_frequency_mode", None),
    ("frequency.distribution", "normal"),
    ("frequency.direct.lognormal.p50", float("inf")),
    ("frequency.direct.pert.mode", None),
    ("cost.direct.pareto.p95", True),
    ("frequency.panel.next_id", 1),
    ("scenarios.next_id", 1),
    ("drafts", {"unknown": "1e"}),
]


@pytest.mark.parametrize(("path", "value"), INVALID_CHANGES)
def test_invalid_schema_rejected(path, value):
    doc = make_document()
    parts = path.split(".")
    target = doc
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    with pytest.raises((ValueError, TypeError)):
        validate_document(doc)


@pytest.mark.parametrize(
    "kind",
    [
        "extra",
        "missing",
        "duplicate_panel",
        "duplicate_scenario",
        "one_panel",
        "no_scenarios",
        "bad_draft",
        "large_integer",
    ],
)
def test_invalid_structures_rejected(kind):
    doc = make_document()
    if kind == "extra":
        doc["extra"] = 1
    elif kind == "missing":
        del doc["cost"]["direct"]["pert"]["min"]
    elif kind == "duplicate_panel":
        doc["cost"]["panel"]["rows"][1]["id"] = 1
    elif kind == "duplicate_scenario":
        doc["scenarios"]["rows"][1]["id"] = 1
    elif kind == "one_panel":
        doc["cost"]["panel"]["rows"].pop()
    elif kind == "no_scenarios":
        doc["scenarios"]["rows"] = []
    elif kind == "bad_draft":
        doc["drafts"]["seed"] = 4
    elif kind == "large_integer":
        doc["cost"]["direct"]["pert"]["min"] = 10**500
    with pytest.raises(ValueError):
        validate_document(doc)


def test_import_is_all_or_nothing_and_limits_bytes():
    good, bad = make_document(), make_document()
    bad["seed"] = -1
    content = json.dumps({"format": LIBRARY_FORMAT, "version": 1, "analyses": [good, bad]})
    with pytest.raises(ValueError):
        parse_backup(content)
    with pytest.raises(ValueError, match="Duplicate"):
        parse_backup(json.dumps({"format": LIBRARY_FORMAT, "version": 1, "analyses": [good, good]}))
    with pytest.raises(ValueError, match="10 MiB"):
        parse_backup(b" " * (MAX_BACKUP_BYTES + 1))
    with pytest.raises(ValueError):
        parse_backup("{broken")
    with pytest.raises(ValueError):
        parse_backup(b"\xff")


def test_integral_json_numbers_use_canonical_draft_paths():
    doc = make_document()
    doc["version"] = 1.0
    doc["frequency"]["panel"]["rows"][0]["id"] = 1.0
    doc["scenarios"]["rows"][0]["id"] = 1.0
    doc["drafts"] = {"frequency:panel:1:p95": "1e", "scenario:integer:1:cost_p95": "-"}
    assert validate_document(doc) is doc
    assert parse_backup(serialize_backup([doc])) == [doc]
