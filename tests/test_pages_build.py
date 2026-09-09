"""Regression coverage for browser startup and publication boundaries."""

import json
import zipfile

import pytest

from scripts import build_pages
from scripts.build_pages import allow_cold_worker_startup, enable_startup, validate_local_wheels


def test_cold_startup_extends_only_the_worker_transport_timeout(tmp_path):
    asset = tmp_path / "state-test.js"
    asset.write_text('transportId:"marimo-transport"}),maxRequestTime:2e4; otherTimeout:2e4')
    allow_cold_worker_startup(tmp_path)
    assert asset.read_text() == (
        'transportId:"marimo-transport"}),maxRequestTime:120000; otherTimeout:2e4'
    )


def test_changed_worker_bundle_requires_review(tmp_path):
    (tmp_path / "state-test.js").write_text("changed exporter output")
    with pytest.raises(ValueError, match="pinned"):
        allow_cold_worker_startup(tmp_path)


def test_export_enables_startup_without_changing_notebook_code():
    config = {"runtime": {"auto_instantiate": False}, "save": {"autosave": "after_delay"}}
    source = "<marimo-code>auto_instantiate = False</marimo-code>"
    html = 'const mount = {"config": ' + json.dumps(config) + "};" + source
    result = enable_startup(html)
    decoded, _ = json.JSONDecoder().raw_decode(result.split('"config": ', 1)[1])
    assert decoded["runtime"]["auto_instantiate"] is True
    assert decoded["save"]["autosave"] == "off"
    assert result.endswith(source)


@pytest.mark.parametrize("html", ["<html></html>", '"config": {}, "config": {}', '"config": {}'])
def test_changed_export_format_fails_instead_of_shipping_a_blank_app(html):
    with pytest.raises(ValueError):
        enable_startup(html)


@pytest.mark.parametrize("unexpected", ["annual_loss/.env", "__marimo__/session/app.py.json"])
def test_bundle_rejects_private_or_generated_files(tmp_path, monkeypatch, unexpected):
    package = tmp_path / "annual_loss"
    package.mkdir()
    (package / "__init__.py").write_text("")
    monkeypatch.setattr(build_pages, "ROOT", tmp_path)
    wheels = tmp_path / "public" / "wheels"
    wheels.mkdir(parents=True)
    with zipfile.ZipFile(wheels / "annual_loss-test.whl", "w") as archive:
        archive.writestr("annual_loss/__init__.py", "")
        archive.writestr(unexpected, "must stay local")
    with pytest.raises(ValueError, match="reviewed"):
        validate_local_wheels(tmp_path)


def test_bundle_requires_all_importable_sources(tmp_path, monkeypatch):
    package = tmp_path / "annual_loss"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "simulation.py").write_text("")
    monkeypatch.setattr(build_pages, "ROOT", tmp_path)
    wheels = tmp_path / "public" / "wheels"
    wheels.mkdir(parents=True)
    with zipfile.ZipFile(wheels / "annual_loss-test.whl", "w") as archive:
        archive.writestr("annual_loss/__init__.py", "")
    with pytest.raises(ValueError, match="reviewed"):
        validate_local_wheels(tmp_path)
