"""Build the interactive GitHub Pages artifact without including local session data."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def allow_cold_worker_startup(assets: Path) -> None:
    """Allow cold Pyodide initialization to finish before the worker RPC times out."""
    marker = 'transportId:"marimo-transport"}),maxRequestTime:2e4'
    matches = [path for path in assets.glob("state-*.js") if marker in path.read_text()]
    if len(matches) != 1:
        raise ValueError("Expected the pinned Marimo worker startup timeout")
    path = matches[0]
    source = path.read_text()
    if source.count(marker) != 1:
        raise ValueError("Expected one Marimo worker transport configuration")
    path.write_text(source.replace(marker, marker.replace("2e4", "120000")))


def enable_startup(html: str) -> str:
    """Override Marimo 0.24's disabled startup in the exported mount configuration.

    The CLI only forwards display settings, so a project runtime setting or an
    environment override does not reach this configuration. Parse the actual JSON
    value rather than replacing text in the embedded notebook source.
    """
    matches = list(re.finditer(r'"config":\s*', html))
    if len(matches) != 1:
        raise ValueError("Expected exactly one Marimo mount configuration")
    start = matches[0].end()
    config, length = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(config.get("runtime"), dict):
        raise ValueError("Export is missing the Marimo runtime configuration")
    config["runtime"]["auto_instantiate"] = True
    config["save"]["autosave"] = "off"
    encoded = json.dumps(config).replace("<", "\\u003c")
    return html[:start] + encoded + html[start + length :]


def validate_local_wheels(directory: Path) -> None:
    """Require exactly the project Python sources, with no private/generated files."""
    wheels = list((directory / "public" / "wheels").glob("*.whl"))
    if len(wheels) != 1 or not wheels[0].name.startswith("annual_loss-"):
        raise ValueError("Expected one bundled annual_loss wheel")
    expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / "annual_loss").glob("*.py")}
    with zipfile.ZipFile(wheels[0]) as wheel:
        sources = {name for name in wheel.namelist() if ".dist-info/" not in name}
    if sources != expected:
        raise ValueError("Bundled sources do not match the reviewed annual_loss package")


def build() -> Path:
    # Marimo automatically copies a notebook's public/ directory. Keep the input
    # explicit so adding an export or local data file cannot silently publish it.
    if (ROOT / "public").exists():
        raise ValueError("Review public/ contents before enabling them in the Pages build")
    destination = ROOT / "dist"
    with tempfile.TemporaryDirectory(prefix="annual-loss-pages-") as temp:
        exported = Path(temp) / "export"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "marimo",
                "export",
                "html-wasm",
                "app.py",
                "--output",
                str(exported),
                "--mode",
                "run",
                "--no-show-code",
                "--no-execute",
            ],
            cwd=ROOT,
            check=True,
        )
        validate_local_wheels(exported)
        html = enable_startup((exported / "index.html").read_text())
        artifact = Path(temp) / "artifact"
        artifact.mkdir()
        (artifact / "index.html").write_text(html)
        (artifact / ".nojekyll").touch()
        shutil.copytree(exported / "assets", artifact / "assets")
        allow_cold_worker_startup(artifact / "assets")
        shutil.copytree(exported / "public" / "wheels", artifact / "public" / "wheels")
        # Include only favicon assets from the export root, not vendor documents.
        for name in ("favicon.ico", "favicon-16x16.png", "favicon-32x32.png"):
            if (exported / name).is_file():
                shutil.copy2(exported / name, artifact / name)
        if destination.is_symlink():
            raise ValueError("Refusing to replace a symlinked dist directory")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(artifact, destination)
    return destination


if __name__ == "__main__":
    print(f"Pages artifact ready: {build()}")
