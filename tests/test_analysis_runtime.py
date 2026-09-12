"""The bridge must preserve the Calculate boundary and reproducible snapshots."""

from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch

import numpy as np
import pytest

from annual_loss.analysis_document import make_document, parse_backup, serialize_backup
from annual_loss.analysis_runtime import AnalysisSession, resolve_document
from annual_loss.models import SimulationConfig
from annual_loss.simulation import simulate_annual_loss, simulate_scenarios
from annual_loss.workflow_state import WorkflowModeState


def request(doc, token="one", action="preview", activation="activation"):
    return {"analysis": deepcopy(doc), "token": token, "action": action, "activation": activation}


def test_preview_and_view_do_not_calculate_annual_loss():
    doc = make_document()
    with patch("annual_loss.analysis_runtime.simulate_annual_loss") as loss:
        session = AnalysisSession()
        result = session.process(request(doc))
        assert result["loss"] is None and not result["errors"]
        doc["view"]["chart"] = "cdf"
        assert session.process(request(doc, "two", "view"))["loss"] is None
        loss.assert_not_called()


def test_calculation_uses_saved_inputs_and_repeat_requests_are_idempotent():
    doc = make_document()
    doc["frequency"]["direct"]["lognormal"] = {"p50": 0.5, "p95": 3}
    doc["seed"] = 9123
    session = AnalysisSession()
    restored = parse_backup(serialize_backup([doc]))[0]
    original_request = request(restored, action="calculate")
    response = session.process(original_request)
    expected = simulate_annual_loss(
        "lognormal",
        doc["frequency"]["direct"]["lognormal"],
        "lognormal",
        doc["cost"]["direct"]["lognormal"],
        config=SimulationConfig(seed=9123),
    )
    np.testing.assert_array_equal(session.result.samples, expected.samples)
    with patch(
        "annual_loss.analysis_runtime.simulate_annual_loss",
        side_effect=AssertionError("duplicate simulation"),
    ):
        assert session.process(original_request) == response
        doc["seed"] = 1
        updated = session.process(request(doc, "two"))
        assert updated["loss"]["meta"] == response["loss"]["meta"]
        assert updated["loss"]["summary"] == response["loss"]["summary"]
    assert restored == original_request["analysis"]


def test_switch_and_reactivation_clear_results():
    doc = make_document()
    session = AnalysisSession()
    assert session.process(request(doc, action="calculate"))["loss"]
    assert session.process(request(doc, "two", activation="new-activation"))["loss"] is None
    assert session.process(request(make_document(), "three"))["loss"] is None


def test_active_drafts_prevent_calculation_but_inactive_drafts_do_not():
    doc = make_document()
    doc["drafts"] = {"cost:direct:pert:min": "-", "scenario:integer:1:name": ""}
    assert not resolve_document(doc)[0]
    doc["drafts"]["frequency:direct:lognormal:p95"] = "1e"
    with patch("annual_loss.analysis_runtime.simulate_annual_loss") as loss:
        result = AnalysisSession().process(request(doc, action="calculate"))
        assert "frequency:direct:lognormal:p95" in result["errors"]
        loss.assert_not_called()


def test_invalid_or_unsafe_inputs_do_not_simulate():
    for p95 in [0, 1e100]:
        doc = make_document()
        doc["frequency"]["direct"]["lognormal"]["p95"] = p95
        with patch("annual_loss.analysis_runtime.simulate_annual_loss") as loss:
            result = AnalysisSession().process(request(doc, action="calculate"))
            assert result["errors"] and result["loss"] is None
            loss.assert_not_called()


def test_scenario_restore_keeps_seed_and_paired_event_costs():
    doc = make_document()
    doc["workflow"] = asdict(WorkflowModeState().select("frequency", "scenario"))
    doc["seed"] = 410
    doc["scenarios"]["rows"][0]["frequency_method"] = "pert"
    doc["scenarios"]["rows"][0]["frequency_max"] = 3
    session = AnalysisSession()
    result = session.process(request(parse_backup(serialize_backup([doc]))[0], action="calculate"))
    assert not result["errors"]
    _, resolved = resolve_document(doc)
    expected = simulate_scenarios(resolved["scenarios"], "loss", config=SimulationConfig(seed=410))
    np.testing.assert_array_equal(session.result.samples, expected.samples)
    assert "Product Exploit" in result["loss"]["summary"]


def test_panel_averages_and_analytics_survive_restore():
    doc = make_document()
    doc["workflow"] = asdict(WorkflowModeState().select("frequency", "panel"))
    doc["frequency"]["panel"]["rows"][0]["p50"] = 2
    doc["frequency"]["panel"]["rows"][1]["p50"] = 4
    errors, model = resolve_document(doc)
    assert not errors and model["frequency_params"]["p50"] == 3
    response = AnalysisSession().process(request(doc, action="calculate"))
    assert not response["errors"] and response["panels"]["frequency"][0]["Average"] == "3"
    assert "Panelist 1" in response["loss"]["summary"]


def test_view_changes_redraw_without_sampling():
    doc = make_document()
    session = AnalysisSession()
    before = session.process(request(doc, action="calculate"))
    doc["view"]["chart"] = "cdf"
    doc["view"]["confidence_level"] = 80
    with patch(
        "annual_loss.analysis_runtime.preview_models",
        side_effect=AssertionError("preview repeated"),
    ):
        after = session.process(request(doc, "two", "view"))
    assert before["loss"]["meta"] == after["loss"]["meta"]
    assert before["loss"]["figure"] != after["loss"]["figure"]
    assert after["loss"]["stats"][0]["label"] == "P10 lower bound"


@pytest.mark.parametrize(
    "change", [{"action": "save-and-run"}, {"activation": None}, {"token": ""}]
)
def test_bad_request_envelopes_are_rejected(change):
    with pytest.raises(ValueError):
        AnalysisSession().process({**request(make_document()), **change})


@pytest.mark.parametrize("scenario", [False, True])
def test_invalid_cost_does_not_remove_valid_frequency_preview(scenario):
    doc = make_document()
    if scenario:
        doc["workflow"] = asdict(WorkflowModeState().select("cost", "scenario"))
        doc["drafts"]["scenario:integer:1:cost_p95"] = "1e"
    else:
        doc["cost"]["direct"]["lognormal"]["p95"] = -1
    response = AnalysisSession().process(request(doc))
    assert response["errors"]
    assert "frequency" in response["previews"]
    assert "cost" not in response["previews"]
    assert response["loss"] is None
