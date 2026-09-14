"""The notebook composes one persistent browser editor, with Python-only modeling."""

import ast
from pathlib import Path

from annual_loss.analysis_browser import BROWSER_MODULE
from annual_loss.analysis_document import make_document
from annual_loss.analysis_styles import HERO_HTML, SHARED_CSS, WORKSPACE_CSS
from annual_loss.analysis_workspace import AnalysisWorkspace, workspace_module
from app import app


def test_notebook_keeps_editor_mount_independent_of_results():
    source = Path("app.py").read_text()
    tree = ast.parse(source)
    cells = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    mount = next(
        cell for cell in cells if "AnalysisWorkspace(" in ast.get_source_segment(source, cell)
    )
    assert "analysis_request" not in {arg.arg for arg in mount.args.args}
    assert "analysis_session.process(analysis_request)" in source
    assert "simulate_annual_loss(" not in source
    _, definitions = app.run()
    assert definitions["workspace"].value["request"] == {}
    assert definitions["analysis_session"].result is None


def test_workspace_bundles_javascript_and_current_design():
    assert "Annual losses from breaches" in HERO_HTML
    assert "Estimate the frequency and impact of future breaches in dollar values." in HERO_HTML
    for token in [
        "--ald-accent:",
        "--ald-risk-accent:",
        "--ald-rose:",
        ".ald-step-header",
        ".ald-scenario-row",
        ".ald-panelist-row",
    ]:
        assert token in SHARED_CSS
    assert "@media" in WORKSPACE_CSS
    module = workspace_module()
    assert "plotly.js v" in module and module.endswith(BROWSER_MODULE)
    assert "data-analysis-result" not in module  # No external notebook DOM manipulation.
    widget = AnalysisWorkspace(defaults=make_document())
    assert widget.response == {} and widget.request == {}


def test_report_and_imported_names_use_text_not_html():
    assert 'results.querySelector(".aw-report").textContent = loss.summary' in BROWSER_MODULE
    assert "element.textContent = text" in BROWSER_MODULE
    assert "navigator.clipboard.writeText(lastLoss.summary)" in BROWSER_MODULE
    assert 'document.execCommand("copy")' in BROWSER_MODULE
    assert ".innerHTML = loss" not in BROWSER_MODULE


def test_sequential_layout_and_calculation_boundary_are_explicit():
    assert 'step(3, "Calculate annual loss"' in BROWSER_MODULE
    assert '["frequency", "cost"].entries()' in BROWSER_MODULE
    assert "Calculate / Recalculate annual loss" in BROWSER_MODULE
    assert 'publish(true, "calculate")' in BROWSER_MODULE
    assert "response.activation !== activation || response.token !== token" in BROWSER_MODULE
    assert 'change:response", acceptResponse' in BROWSER_MODULE
