# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo==0.24.0",
#     "numpy>=2,<3",
#     "plotly>=6,<7",
#     "scipy>=1.15,<2",
#     "anywidget>=0.9,<1",
#     "traitlets>=5,<6",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full", app_title="Annual losses from breaches")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from annual_loss.analysis_document import make_document
    from annual_loss.analysis_runtime import AnalysisSession
    from annual_loss.analysis_styles import HERO_HTML, SHARED_CSS
    from annual_loss.analysis_workspace import AnalysisWorkspace
    from annual_loss.reporting import section_guidance

    return (
        AnalysisSession,
        AnalysisWorkspace,
        HERO_HTML,
        SHARED_CSS,
        make_document,
        mo,
        section_guidance,
    )


@app.cell(hide_code=True)
def _(HERO_HTML, SHARED_CSS, mo):
    mo.Html(f"<style>{SHARED_CSS}</style>{HERO_HTML}")
    return


@app.cell(hide_code=True)
def _(AnalysisSession, AnalysisWorkspace, make_document, mo, section_guidance):
    # This cell never depends on requests or results: its editor stays mounted.
    workspace = mo.ui.anywidget(
        AnalysisWorkspace(
            defaults=make_document(),
            guidance={section: section_guidance(section) for section in ("frequency", "cost")},
        )
    )
    analysis_session = AnalysisSession()
    return analysis_session, workspace


@app.cell(hide_code=True)
def _(mo, workspace):
    mo.Html(f'<main class="ald-shell">{workspace}</main>')
    return


@app.cell(hide_code=True)
def _(workspace):
    analysis_request = workspace.value.get("request", {})
    return (analysis_request,)


@app.cell(hide_code=True)
def _(analysis_request, analysis_session, workspace):
    # Preview/view requests cannot enter the full annual-loss simulation path.
    # Responses carry the activation and request identities used by the browser.
    if analysis_request:
        workspace.widget.response = analysis_session.process(analysis_request)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html("""<footer class="ald-footer">This tool models elicited assumptions; it is not a forecast,
    accounting opinion, or substitute for professional risk judgment. Analyses save in this
    browser profile. Download a backup to keep elsewhere.</footer>""")
    return


if __name__ == "__main__":
    app.run()
