"""Supported AnyWidget bridge; all editable state belongs to the browser."""

from functools import lru_cache

import anywidget
import traitlets
from plotly.offline import get_plotlyjs

from .analysis_browser import BROWSER_MODULE
from .analysis_styles import WORKSPACE_CSS


@lru_cache(maxsize=1)
def workspace_module():
    # Use the JS shipped with the locked Plotly Python package. No CDN, global
    # Plotly dependency, or notebook DOM introspection is needed in either runtime.
    return (
        "const Plotly = (() => { const module = {exports: {}};\n"
        + get_plotlyjs()
        + "\nreturn module.exports; })();\n"
        + BROWSER_MODULE
    )


class AnalysisWorkspace(anywidget.AnyWidget):
    defaults = traitlets.Dict().tag(sync=True)
    guidance = traitlets.Dict().tag(sync=True)
    request = traitlets.Dict().tag(sync=True)
    response = traitlets.Dict().tag(sync=True)
    _css = WORKSPACE_CSS

    def __init__(self, **kwargs):
        super().__init__(_esm=workspace_module(), **kwargs)
