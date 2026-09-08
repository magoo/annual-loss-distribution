import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full", app_title="Annual losses from breaches")


@app.cell(hide_code=True)
def _():
    import json
    from collections.abc import Mapping
    from dataclasses import asdict, is_dataclass

    import marimo as mo

    from annual_loss import (
        DEFAULT_SCENARIOS,
        AnnualLossError,
        EmpiricalCDF,
        Scenario,
        SimulationConfig,
        average_panel_params,
        confidence_interval,
        distribution_curve,
        panel_analytics,
        simulate_annual_loss,
        simulate_scenarios,
        validate_params,
    )
    from annual_loss.charts import build_distribution_figure
    from annual_loss.formatting import format_compact, format_value
    from annual_loss.panel_editor import PanelEditorState
    from annual_loss.reporting import (
        build_executive_summary,
        confidence_statement,
        section_guidance,
    )
    from annual_loss.scenario_editor import (
        ScenarioEditorState,
        cost_parameter_fields,
        frequency_parameter_fields,
    )
    from annual_loss.workflow_state import WorkflowModeState

    return (
        DEFAULT_SCENARIOS,
        AnnualLossError,
        EmpiricalCDF,
        Mapping,
        PanelEditorState,
        Scenario,
        ScenarioEditorState,
        SimulationConfig,
        WorkflowModeState,
        asdict,
        average_panel_params,
        build_distribution_figure,
        build_executive_summary,
        confidence_interval,
        confidence_statement,
        cost_parameter_fields,
        distribution_curve,
        format_compact,
        format_value,
        frequency_parameter_fields,
        is_dataclass,
        json,
        mo,
        panel_analytics,
        section_guidance,
        simulate_annual_loss,
        simulate_scenarios,
        validate_params,
    )


@app.cell(hide_code=True)
def _(DEFAULT_SCENARIOS, Mapping, asdict, is_dataclass):
    MODE_OPTIONS = {
        "Direct estimate": "direct",
        "Expert panel": "panel",
        "Threat scenarios": "scenario",
    }
    DISTRIBUTION_OPTIONS = {
        "Lognormal": "lognormal",
        "PERT": "pert",
        "Pareto": "pareto",
    }
    DISTRIBUTION_LABELS = {
        "lognormal": "Lognormal",
        "pert": "PERT",
        "pareto": "Pareto",
    }
    DEFAULT_PARAMETERS = {
        ("frequency", "lognormal"): {"p50": 1.0, "p95": 10.0},
        ("frequency", "pareto"): {"p50": 1.0, "p95": 10.0},
        ("frequency", "pert"): {"min": 0.0, "mode": 1.0, "max": 10.0},
        ("cost", "lognormal"): {"p50": 50_000.0, "p95": 500_000.0},
        ("cost", "pareto"): {"p50": 50_000.0, "p95": 500_000.0},
        ("cost", "pert"): {
            "min": 1_000.0,
            "mode": 50_000.0,
            "max": 500_000.0,
        },
    }
    PARAMETER_LABELS = {
        "frequency": {
            "p50": "P50 median incidents/year",
            "p95": "P95 incidents/year",
            "min": "Minimum incidents/year",
            "mode": "Most likely incidents/year",
            "max": "Maximum incidents/year",
        },
        "cost": {
            "p50": "P50 median cost ($)",
            "p95": "P95 cost ($)",
            "min": "Minimum cost ($)",
            "mode": "Most likely cost ($)",
            "max": "Maximum cost ($)",
        },
    }

    def parameter_fields(distribution):
        return ("min", "mode", "max") if distribution == "pert" else ("p50", "p95")

    def parameter_defaults(section, distribution):
        return dict(DEFAULT_PARAMETERS[(section, distribution)])

    def object_mapping(value):
        if isinstance(value, Mapping):
            return dict(value)
        if is_dataclass(value):
            return asdict(value)
        return {
            key: getattr(value, key)
            for key in ("odds", "p50", "p95", "min", "mode", "max")
            if hasattr(value, key)
        }

    def scenario_row(scenario):
        frequency = object_mapping(scenario.frequency_params)
        cost = object_mapping(scenario.cost_params)
        return {
            "id": scenario.id,
            "name": scenario.name,
            "frequency_method": getattr(
                scenario.frequency_method, "value", scenario.frequency_method
            ),
            "frequency_odds": frequency.get("odds", 10.0),
            "frequency_p50": frequency.get("p50", 1.0),
            "frequency_p95": frequency.get("p95", 10.0),
            "frequency_min": frequency.get("min", 0.0),
            "frequency_mode": frequency.get("mode", 1.0),
            "frequency_max": frequency.get("max", 10.0),
            "cost_dist_type": getattr(scenario.cost_dist_type, "value", scenario.cost_dist_type),
            "cost_p50": cost.get("p50", 50_000.0),
            "cost_p95": cost.get("p95", 500_000.0),
            "cost_min": cost.get("min", 1_000.0),
            "cost_mode": cost.get("mode", 50_000.0),
            "cost_max": cost.get("max", 500_000.0),
        }

    DEFAULT_SCENARIO_ROWS = [scenario_row(item) for item in DEFAULT_SCENARIOS]
    DEFAULT_PANEL_ROWS = {
        "frequency": [
            {
                "id": index,
                "name": f"Panelist {index}",
                "p50": 1.0,
                "p95": 10.0,
                "min": 0.0,
                "mode": 1.0,
                "max": 10.0,
            }
            for index in (1, 2)
        ],
        "cost": [
            {
                "id": index,
                "name": f"Panelist {index}",
                "p50": 50_000.0,
                "p95": 500_000.0,
                "min": 1_000.0,
                "mode": 50_000.0,
                "max": 500_000.0,
            }
            for index in (1, 2)
        ],
    }

    return (
        DEFAULT_PARAMETERS,
        DEFAULT_PANEL_ROWS,
        DEFAULT_SCENARIO_ROWS,
        DISTRIBUTION_LABELS,
        DISTRIBUTION_OPTIONS,
        MODE_OPTIONS,
        PARAMETER_LABELS,
        parameter_defaults,
        parameter_fields,
    )


@app.cell(hide_code=True)
def _(json, mo):
    def copy_button(text):
        payload = json.dumps(text).replace("<", "\\u003c")
        document = """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="color-scheme" content="light dark" />
            <title>Copy executive summary</title>
            <style>
              * { box-sizing: border-box; }
              html, body { margin: 0; overflow: hidden; }
              body {
                align-items: flex-start;
                background: transparent;
                display: flex;
                font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                  "Segoe UI", sans-serif;
                padding: .2rem;
              }
              button {
                background: Canvas;
                border: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
                border-radius: .4rem;
                color: CanvasText;
                cursor: pointer;
                font: 650 .82rem/1 ui-sans-serif, system-ui, sans-serif;
                height: 2rem;
                padding: 0 .8rem;
                width: 100%;
              }
              button:hover { background: color-mix(in srgb, Canvas 94%, CanvasText 6%); }
              button:disabled { cursor: wait; opacity: .7; }
              button:focus-visible {
                outline: 3px solid color-mix(in srgb, #4f5fbf 45%, transparent);
                outline-offset: 1px;
              }
              button[data-state="success"] { color: #067647; }
              button[data-state="error"] { color: #b42318; }
              .sr-only {
                border: 0;
                clip: rect(0, 0, 0, 0);
                height: 1px;
                margin: -1px;
                overflow: hidden;
                padding: 0;
                position: absolute;
                white-space: nowrap;
                width: 1px;
              }
            </style>
          </head>
          <body>
            <button
              id="copy-report"
              data-testid="copy-executive-summary"
              type="button"
              aria-describedby="copy-status"
              aria-label="Copy executive summary to clipboard"
              title="Copy executive summary"
            >Copy</button>
            <span id="copy-status" class="sr-only" aria-live="polite"></span>
            <script>
              const reportText = __REPORT_TEXT_JSON__;
              const button = document.getElementById("copy-report");
              const status = document.getElementById("copy-status");
              let resetTimer;

              function setFeedback(label, state, announcement) {
                window.clearTimeout(resetTimer);
                button.textContent = label;
                button.dataset.state = state;
                status.textContent = announcement;
                resetTimer = window.setTimeout(() => {
                  button.textContent = "Copy";
                  button.dataset.state = "idle";
                  status.textContent = "";
                }, 1800);
              }

              function copyWithSelection() {
                const textarea = document.createElement("textarea");
                textarea.value = reportText;
                textarea.setAttribute("readonly", "");
                textarea.style.cssText = "position:fixed;left:-9999px;top:0";
                document.body.appendChild(textarea);
                textarea.focus({ preventScroll: true });
                textarea.select();
                textarea.setSelectionRange(0, textarea.value.length);
                const copied = document.execCommand("copy");
                textarea.remove();
                return copied;
              }

              async function writeReport() {
                let clipboardError;
                if (navigator.clipboard?.writeText) {
                  try {
                    await navigator.clipboard.writeText(reportText);
                    return;
                  } catch (error) {
                    clipboardError = error;
                  }
                }
                if (!copyWithSelection()) {
                  throw clipboardError ?? new Error("Clipboard write failed");
                }
              }

              button.addEventListener("click", async () => {
                button.disabled = true;
                try {
                  await writeReport();
                  setFeedback("Copied", "success", "Executive summary copied to clipboard.");
                } catch (error) {
                  setFeedback("Try again", "error", "Could not copy the executive summary.");
                } finally {
                  button.disabled = false;
                }
              });
            </script>
          </body>
        </html>
        """.replace("__REPORT_TEXT_JSON__", payload, 1)
        frame = mo.iframe(document, width="104px", height="40px")
        return mo.Html(
            frame.text.replace(
                "<iframe ",
                '<iframe title="Copy executive summary" allow="clipboard-write" ',
                1,
            )
        )

    def surface(content, class_name=""):
        classes = "ald-surface"
        if class_name:
            classes = f"{classes} {class_name}"
        return mo.Html(f'<section class="{classes}">{content}</section>')

    def step_header(step, title, description):
        return mo.Html(
            f"""
            <header class="ald-step-header">
              <span class="ald-kicker">Step {step}</span>
              <h2>{title}</h2>
              <p>{description}</p>
            </header>
            """
        )

    def panel_heading(title, description):
        return mo.Html(
            f"""
            <div class="ald-panel-heading">
              <strong>{title}</strong>
              <span>{description}</span>
            </div>
            """
        )

    hero = mo.Html(
        """
        <style>
          :root {
            --ald-accent: #4f5fbf;
            --ald-risk-accent: #B42318;
            --ald-rose: #d84b73;
            --ald-ink: var(--foreground, #202534);
            --ald-muted: var(--muted-foreground, #667085);
            --ald-border: color-mix(in srgb, var(--foreground, #202534) 13%, transparent);
            --ald-surface: color-mix(
              in srgb, var(--background, #ffffff) 97%, var(--foreground, #202534) 3%
            );
            --ald-surface-soft: color-mix(
              in srgb, var(--background, #ffffff) 93%, var(--ald-accent) 7%
            );
          }

          .ald-hero,
          .ald-shell,
          .ald-footer {
            box-sizing: border-box;
            margin-inline: auto;
            max-width: 72rem;
            width: 100%;
          }

          .ald-hero {
            padding: clamp(1.25rem, 4vw, 3rem) clamp(.4rem, 2vw, 1rem) 1.25rem;
          }

          .ald-eyebrow,
          .ald-kicker {
            color: var(--ald-risk-accent);
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .12em;
            text-transform: uppercase;
          }

          .ald-hero h1,
          .ald-step-header h2 {
            color: var(--ald-ink);
            font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
            letter-spacing: -.035em;
          }

          .ald-hero h1 {
            font-size: clamp(2rem, 5vw, 3.75rem);
            line-height: 1.02;
            margin: .45rem 0 .7rem;
            max-width: 15ch;
          }

          .ald-hero > p {
            color: var(--ald-muted);
            font-size: clamp(1rem, 2vw, 1.15rem);
            line-height: 1.65;
            margin: 0;
            max-width: 46rem;
          }

          .ald-shell {
            padding: 0 clamp(.35rem, 2vw, 1rem) 2rem;
          }

          .ald-surface {
            background: var(--ald-surface);
            border: 1px solid var(--ald-border);
            border-radius: 12px;
            padding: clamp(.9rem, 2.5vw, 1.35rem);
          }

          .ald-scenario-list,
          .ald-panelist-list {
            display: flex;
            flex-direction: column;
            gap: .8rem;
          }

          .ald-scenario-row,
          .ald-panelist-row {
            align-items: start;
            background: color-mix(
              in srgb, var(--background, #ffffff) 98%, var(--ald-accent) 2%
            );
            border: 1px solid var(--ald-border);
            border-radius: 10px;
            display: grid;
            gap: 1rem;
            padding: 1rem;
          }

          .ald-scenario-row--two-models {
            grid-template-columns:
              minmax(12rem, .85fr) minmax(18rem, 1fr) minmax(18rem, 1fr);
          }

          .ald-scenario-row--with-actions {
            grid-template-columns:
              minmax(12rem, .85fr) minmax(18rem, 1fr) minmax(18rem, 1fr) auto;
          }

          .ald-panelist-row {
            grid-template-columns: minmax(12rem, .8fr) minmax(22rem, 2fr);
          }

          .ald-panelist-row--with-actions {
            grid-template-columns: minmax(12rem, .8fr) minmax(22rem, 2fr) auto;
          }

          .ald-scenario-group,
          .ald-panelist-group {
            min-width: 0;
          }

          .ald-scenario-group-label,
          .ald-panelist-group-label {
            color: var(--ald-muted);
            display: block;
            font-size: .7rem;
            font-weight: 750;
            letter-spacing: .08em;
            margin-bottom: .5rem;
            text-transform: uppercase;
          }

          .ald-scenario-actions,
          .ald-panelist-actions {
            align-self: end;
          }

          .ald-scenario-editor button,
          .ald-panel-editor button {
            white-space: nowrap;
          }

          .ald-toolbar {
            background: var(--ald-surface-soft);
            padding-block: .75rem;
          }

          .ald-toolbar .ald-panel-heading {
            margin-bottom: 0;
            min-width: 0;
          }

          .ald-toolbar .ald-panel-heading span {
            max-width: 16rem;
          }

          .ald-toolbar marimo-radio::part(label),
          .ald-toolbar marimo-slider::part(label) {
            white-space: nowrap;
          }

          .ald-panel-heading {
            margin-bottom: .85rem;
          }

          .ald-panel-heading strong {
            color: var(--ald-ink);
            display: block;
            font-size: .92rem;
          }

          .ald-panel-heading span {
            color: var(--ald-muted);
            display: block;
            font-size: .8rem;
            margin-top: .15rem;
          }

          .ald-step-header {
            border-left: 3px solid var(--ald-risk-accent);
            padding: .1rem 0 .1rem .9rem;
          }

          .ald-step-header h2 {
            font-size: clamp(1.45rem, 3vw, 2rem);
            line-height: 1.15;
            margin: .2rem 0 .35rem;
          }

          .ald-step-header p {
            color: var(--ald-muted);
            line-height: 1.55;
            margin: 0;
            max-width: 52rem;
          }

          .ald-insight {
            background: var(--ald-surface-soft);
            border-left: 3px solid var(--ald-rose);
            border-radius: 8px;
            color: var(--ald-ink);
            line-height: 1.5;
            padding: .75rem .9rem;
          }

          .ald-insight strong {
            color: var(--ald-rose);
            display: block;
            font-size: .7rem;
            letter-spacing: .1em;
            margin-bottom: .2rem;
            text-transform: uppercase;
          }

          .ald-narrative {
            background: var(--ald-surface-soft);
            border: 1px solid var(--ald-border);
            border-radius: 10px;
            padding: .85rem 1rem;
          }

          .ald-narrative h3 {
            color: var(--ald-ink);
            font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
            font-size: 1.05rem;
            margin: 0 0 .55rem;
          }

          .ald-narrative ul {
            color: var(--ald-muted);
            margin: 0;
            padding-left: 1.15rem;
          }

          .ald-narrative li + li { margin-top: .35rem; }
          .ald-meta {
            color: var(--ald-muted);
            font-size: .8rem;
            line-height: 1.55;
          }

          .ald-shell :focus-visible {
            outline: 3px solid color-mix(in srgb, var(--ald-accent) 45%, transparent);
            outline-offset: 2px;
          }

          .ald-footer {
            border-top: 1px solid var(--ald-border);
            color: var(--ald-muted);
            font-size: .8rem;
            line-height: 1.55;
            padding: 1rem clamp(.4rem, 2vw, 1rem) 2rem;
          }

          @media (max-width: 80rem) {
            .ald-toolbar > div { flex-wrap: wrap !important; }
            .ald-toolbar > div > div {
              flex: 1 1 calc(50% - .375rem) !important;
              min-width: 0;
            }
            .ald-toolbar marimo-radio::part(label),
            .ald-toolbar marimo-slider::part(label) {
              white-space: normal;
            }
          }

          @media (max-width: 64rem) {
            .ald-scenario-row--two-models,
            .ald-scenario-row--with-actions,
            .ald-panelist-row,
            .ald-panelist-row--with-actions {
              grid-template-columns: 1fr;
            }

            .ald-scenario-actions,
            .ald-panelist-actions {
              justify-self: start;
            }
          }

          @media (max-width: 42rem) {
            .ald-hero { padding-top: 1rem; }
            .ald-hero h1 { max-width: 12ch; }
            .ald-surface { border-radius: 10px; padding: .85rem; }
            .ald-toolbar > div {
              align-items: stretch !important;
              flex-direction: column !important;
            }
            .ald-toolbar > div > div {
              flex: none !important;
              width: 100%;
            }
            .ald-toolbar .ald-panel-heading { min-width: 0; }
          }
        </style>
        <div class="ald-hero">
          <span class="ald-eyebrow">Security risk modeling</span>
          <h1>Annual losses from breaches</h1>
          <p>Estimate the frequency and impact of future breaches in dollar values.</p>
        </div>
        """
    )
    hero
    return copy_button, panel_heading, step_header, surface


@app.cell(hide_code=True)
def _(WorkflowModeState, mo):
    get_workflow_mode_state, set_workflow_mode_state = mo.state(
        WorkflowModeState(),
        allow_self_loops=True,
    )
    return get_workflow_mode_state, set_workflow_mode_state


@app.cell(hide_code=True)
def _(MODE_OPTIONS, get_workflow_mode_state, mo, set_workflow_mode_state):
    def mode_label(value):
        return next(label for label, option in MODE_OPTIONS.items() if option == value)

    def mode_handler(section):
        return lambda selected: set_workflow_mode_state(
            get_workflow_mode_state().select(section, selected)
        )

    _workflow_mode_state = get_workflow_mode_state()
    frequency_mode = mo.ui.radio(
        MODE_OPTIONS,
        value=mode_label(_workflow_mode_state.frequency_mode),
        inline=True,
        label="Frequency input source",
        on_change=mode_handler("frequency"),
    )
    cost_mode = mo.ui.radio(
        MODE_OPTIONS,
        value=mode_label(_workflow_mode_state.cost_mode),
        inline=True,
        label="Cost input source",
        on_change=mode_handler("cost"),
    )
    scenario_mode = _workflow_mode_state.scenario_mode
    return cost_mode, frequency_mode, scenario_mode


@app.cell(hide_code=True)
def _(DISTRIBUTION_OPTIONS, mo):
    frequency_distribution = mo.ui.dropdown(
        DISTRIBUTION_OPTIONS,
        value="Lognormal",
        label="Frequency distribution",
    )
    cost_distribution = mo.ui.dropdown(
        DISTRIBUTION_OPTIONS,
        value="Lognormal",
        label="Cost distribution",
    )
    chart_view = mo.ui.radio(
        {"Histogram": "pdf", "CDF": "cdf"},
        value="Histogram",
        inline=True,
        label="Chart view",
    )
    focus_percentile = mo.ui.slider(
        start=95.0,
        stop=99.9,
        step=0.1,
        value=99.5,
        show_value=True,
        label="Outcome percentile",
    )
    confidence_level = mo.ui.slider(
        start=50,
        stop=95,
        step=1,
        value=90,
        show_value=True,
        label="Central range (%)",
    )
    simulation_seed = mo.ui.number(
        start=0,
        step=1,
        value=12_345,
        debounce=True,
        label="Reproducibility seed",
    )
    return (
        chart_view,
        confidence_level,
        cost_distribution,
        focus_percentile,
        frequency_distribution,
        simulation_seed,
    )


@app.cell(hide_code=True)
def _(chart_view, confidence_level, focus_percentile, mo, panel_heading, surface):
    view_controls = surface(
        mo.hstack(
            [
                panel_heading(
                    "View controls",
                    "Updates every preview and result chart.",
                ),
                chart_view,
                focus_percentile,
                confidence_level,
            ],
            justify="start",
            align="center",
            wrap=False,
            gap=0.5,
            widths=[0.95, 1.35, 1.75, 1.6],
        ),
        "ald-toolbar",
    )
    return (view_controls,)


@app.cell(hide_code=True)
def _(
    PARAMETER_LABELS,
    mo,
    parameter_defaults,
    parameter_fields,
):
    def make_parameter_editor(section, distribution):
        defaults = parameter_defaults(section, distribution)
        return mo.ui.dictionary(
            {
                field: mo.ui.number(
                    start=0,
                    step=1,
                    value=defaults[field],
                    debounce=True,
                    label=PARAMETER_LABELS[section][field],
                    full_width=True,
                )
                for field in parameter_fields(distribution)
            },
            label=f"{section.title()} parameters",
        )

    return (make_parameter_editor,)


@app.cell(hide_code=True)
def _(frequency_distribution, make_parameter_editor):
    frequency_parameters = make_parameter_editor("frequency", frequency_distribution.value)
    return (frequency_parameters,)


@app.cell(hide_code=True)
def _(cost_distribution, make_parameter_editor):
    cost_parameters = make_parameter_editor("cost", cost_distribution.value)
    return (cost_parameters,)


@app.cell(hide_code=True)
def _(DEFAULT_PANEL_ROWS, PanelEditorState, mo):
    get_frequency_panel_state, set_frequency_panel_state = mo.state(
        PanelEditorState.from_rows(DEFAULT_PANEL_ROWS["frequency"]),
        allow_self_loops=True,
    )
    get_cost_panel_state, set_cost_panel_state = mo.state(
        PanelEditorState.from_rows(DEFAULT_PANEL_ROWS["cost"]),
        allow_self_loops=True,
    )
    return (
        get_cost_panel_state,
        get_frequency_panel_state,
        set_cost_panel_state,
        set_frequency_panel_state,
    )


@app.cell(hide_code=True)
def _(PARAMETER_LABELS, mo):
    def panel_key(panelist_id):
        prefix = "string" if isinstance(panelist_id, str) else "integer"
        return f"{prefix}:{panelist_id}"

    def make_panel_form(row, section):
        is_cost = section == "cost"
        return mo.ui.dictionary(
            {
                "name": mo.ui.text(
                    value=row.name,
                    label="Panelist name",
                    placeholder="Name this panelist",
                    debounce=True,
                    full_width=True,
                ),
                **{
                    field: mo.ui.number(
                        start=0,
                        step=1_000 if is_cost else 1,
                        value=getattr(row, field),
                        debounce=True,
                        label=PARAMETER_LABELS[section][field],
                        full_width=True,
                    )
                    for field in ("p50", "p95", "min", "mode", "max")
                },
            }
        )

    return make_panel_form, panel_key


@app.cell(hide_code=True)
def _(get_frequency_panel_state, make_panel_form, mo, panel_key):
    frequency_panel_structure = get_frequency_panel_state()
    frequency_panel_keys = tuple(panel_key(row.id) for row in frequency_panel_structure.rows)
    frequency_panel_id_by_key = {
        panel_key(row.id): row.id for row in frequency_panel_structure.rows
    }
    frequency_panel_forms = mo.ui.dictionary(
        {
            panel_key(row.id): make_panel_form(row, "frequency")
            for row in frequency_panel_structure.rows
        },
        label="Frequency expert estimates",
    )
    return (
        frequency_panel_forms,
        frequency_panel_id_by_key,
        frequency_panel_keys,
        frequency_panel_structure,
    )


@app.cell(hide_code=True)
def _(get_cost_panel_state, make_panel_form, mo, panel_key):
    cost_panel_structure = get_cost_panel_state()
    cost_panel_keys = tuple(panel_key(row.id) for row in cost_panel_structure.rows)
    cost_panel_id_by_key = {panel_key(row.id): row.id for row in cost_panel_structure.rows}
    cost_panel_forms = mo.ui.dictionary(
        {panel_key(row.id): make_panel_form(row, "cost") for row in cost_panel_structure.rows},
        label="Cost expert estimates",
    )
    return (
        cost_panel_forms,
        cost_panel_id_by_key,
        cost_panel_keys,
        cost_panel_structure,
    )


@app.cell(hide_code=True)
def _(
    DEFAULT_PANEL_ROWS,
    cost_distribution,
    cost_panel_forms,
    cost_panel_id_by_key,
    cost_panel_keys,
    cost_panel_structure,
    frequency_distribution,
    frequency_panel_forms,
    frequency_panel_id_by_key,
    frequency_panel_keys,
    frequency_panel_structure,
    mo,
    parameter_fields,
    set_cost_panel_state,
    set_frequency_panel_state,
):
    def _panel_rows(forms, keys, id_by_key):
        return [{"id": id_by_key[key], **dict(forms.value[key])} for key in keys]

    def _panel_group(label, content, class_name=""):
        classes = "ald-panelist-group"
        if class_name:
            classes = f"{classes} {class_name}"
        return mo.Html(
            f"""
            <div class="{classes}">
              <span class="ald-panelist-group-label">{label}</span>
              {content}
            </div>
            """
        )

    def _panel_editor(
        section,
        distribution,
        rows,
        structure,
        keys,
        id_by_key,
        forms,
        setter,
    ):
        def current_structure():
            return structure.with_rows(rows)

        def remove_handler(panelist_id):
            return lambda _: setter(current_structure().remove_panelist(panelist_id))

        _row_views = []
        _delete_buttons = {}
        _can_delete = len(rows) > 2
        for _index, _panel_key_value in enumerate(keys, start=1):
            _panelist_id = id_by_key[_panel_key_value]
            _controls = forms[_panel_key_value]
            _estimate_controls = [_controls[field] for field in parameter_fields(distribution)]
            _groups = [
                _panel_group(f"Panelist {_index}", _controls["name"]),
                _panel_group(
                    "Estimate",
                    mo.hstack(
                        _estimate_controls,
                        justify="start",
                        align="end",
                        wrap=True,
                        gap=0.75,
                        widths="equal",
                    ),
                ),
            ]
            if _can_delete:
                _delete_button = mo.ui.button(
                    label="Delete panelist",
                    kind="danger",
                    tooltip=f"Delete panelist {_index}",
                    on_click=remove_handler(_panelist_id),
                )
                _delete_buttons[_panelist_id] = _delete_button
                _groups.append(_panel_group("Actions", _delete_button, "ald-panelist-actions"))
            _row_class = "ald-panelist-row"
            if _can_delete:
                _row_class += " ald-panelist-row--with-actions"
            _row_views.append(
                mo.Html(
                    f"""
                    <article class="{_row_class}" role="listitem">
                      {"".join(group.text for group in _groups)}
                    </article>
                    """
                )
            )

        _defaults = {
            field: DEFAULT_PANEL_ROWS[section][0][field]
            for field in ("p50", "p95", "min", "mode", "max")
        }
        _add_button = mo.ui.button(
            label="Add panelist",
            kind="success",
            tooltip="Append another independent expert estimate",
            on_click=lambda _: setter(current_structure().add_panelist(_defaults)),
        )
        _panel_list = mo.Html(
            f'<div class="ald-panelist-list" role="list">'
            f"{''.join(view.text for view in _row_views)}</div>"
        )
        _panel_footer = mo.hstack(
            [
                mo.md(f"*{len(rows)} panelists in this local session. At least two are required.*"),
                _add_button,
            ],
            justify="space-between",
            align="center",
            wrap=True,
            gap=0.75,
        )
        _panel_view = mo.Html(f'<div class="ald-panel-editor">{_panel_list}{_panel_footer}</div>')
        # Raw mo.Html retains rendered markup, not the UIElement instances. Marimo's
        # UI registry uses weak references, so this mapping deliberately owns every
        # action control for as long as its rendered editor is alive.
        _actions = {"add": _add_button, "delete": _delete_buttons}
        return _panel_view, _actions

    frequency_panel_rows = _panel_rows(
        frequency_panel_forms,
        frequency_panel_keys,
        frequency_panel_id_by_key,
    )
    cost_panel_rows = _panel_rows(
        cost_panel_forms,
        cost_panel_keys,
        cost_panel_id_by_key,
    )
    frequency_panel, frequency_panel_actions = _panel_editor(
        "frequency",
        frequency_distribution.value,
        frequency_panel_rows,
        frequency_panel_structure,
        frequency_panel_keys,
        frequency_panel_id_by_key,
        frequency_panel_forms,
        set_frequency_panel_state,
    )
    cost_panel, cost_panel_actions = _panel_editor(
        "cost",
        cost_distribution.value,
        cost_panel_rows,
        cost_panel_structure,
        cost_panel_keys,
        cost_panel_id_by_key,
        cost_panel_forms,
        set_cost_panel_state,
    )
    return (
        cost_panel,
        cost_panel_actions,
        cost_panel_rows,
        frequency_panel,
        frequency_panel_actions,
        frequency_panel_rows,
    )


@app.cell(hide_code=True)
def _(DEFAULT_SCENARIO_ROWS, ScenarioEditorState, mo):
    get_scenario_editor_state, set_scenario_editor_state = mo.state(
        ScenarioEditorState.from_rows(DEFAULT_SCENARIO_ROWS)
    )
    return get_scenario_editor_state, set_scenario_editor_state


@app.cell(hide_code=True)
def _(
    get_scenario_editor_state,
    mo,
):
    frequency_method_options = {
        "1 in N years": "odds",
        "Lognormal (P50 / P95)": "lognormal",
        "PERT (minimum / likely / maximum)": "pert",
        "Pareto (P50 / P95)": "pareto",
    }
    cost_method_options = {
        "Lognormal (P50 / P95)": "lognormal",
        "PERT (minimum / likely / maximum)": "pert",
        "Pareto (P50 / P95)": "pareto",
    }
    frequency_field_labels = {
        "odds": "One incident every N years",
        "p50": "P50 median incidents/year",
        "p95": "P95 incidents/year",
        "min": "Minimum incidents/year",
        "mode": "Most likely incidents/year",
        "max": "Maximum incidents/year",
    }
    cost_field_labels = {
        "p50": "P50 median cost ($)",
        "p95": "P95 cost ($)",
        "min": "Minimum cost ($)",
        "mode": "Most likely cost ($)",
        "max": "Maximum cost ($)",
    }

    def option_label(options, value):
        return next(label for label, option in options.items() if option == value)

    def number_editor(row, section, field):
        key = f"{section}_{field}"
        is_cost = section == "cost"
        labels = cost_field_labels if is_cost else frequency_field_labels
        return mo.ui.number(
            start=1 if field == "odds" else 0,
            step=1_000 if is_cost else 1,
            value=getattr(row, key),
            debounce=True,
            label=labels[field],
            full_width=True,
        )

    def make_scenario_form(row):
        elements = {
            "name": mo.ui.text(
                value=row.name,
                label="Scenario name",
                placeholder="Name this threat scenario",
                debounce=True,
                full_width=True,
            ),
            "frequency_method": mo.ui.dropdown(
                frequency_method_options,
                value=option_label(frequency_method_options, row.frequency_method),
                allow_select_none=False,
                label="Frequency method",
                full_width=True,
            ),
        }
        elements.update(
            {
                f"frequency_{field}": number_editor(row, "frequency", field)
                for field in frequency_field_labels
            }
        )
        elements["cost_dist_type"] = mo.ui.dropdown(
            cost_method_options,
            value=option_label(cost_method_options, row.cost_dist_type),
            allow_select_none=False,
            label="Cost distribution",
            full_width=True,
        )
        elements.update(
            {f"cost_{field}": number_editor(row, "cost", field) for field in cost_field_labels}
        )
        return mo.ui.dictionary(elements)

    def scenario_key(scenario_id):
        prefix = "string" if isinstance(scenario_id, str) else "integer"
        return f"{prefix}:{scenario_id}"

    scenario_structure = get_scenario_editor_state()
    scenario_keys = tuple(scenario_key(row.id) for row in scenario_structure.rows)
    scenario_id_by_key = {scenario_key(row.id): row.id for row in scenario_structure.rows}
    scenario_forms = mo.ui.dictionary(
        {scenario_key(row.id): make_scenario_form(row) for row in scenario_structure.rows},
        label="Threat scenarios",
    )
    return (
        cost_field_labels,
        frequency_field_labels,
        scenario_forms,
        scenario_id_by_key,
        scenario_keys,
        scenario_structure,
    )


@app.cell(hide_code=True)
def _(
    Scenario,
    cost_field_labels,
    cost_parameter_fields,
    frequency_field_labels,
    frequency_parameter_fields,
    mo,
    panel_heading,
    scenario_forms,
    scenario_id_by_key,
    scenario_keys,
    scenario_structure,
    set_scenario_editor_state,
    surface,
    validate_params,
):
    scenario_rows = [
        {"id": scenario_id_by_key[key], **dict(scenario_forms.value[key])} for key in scenario_keys
    ]

    def validation_message(errors, labels):
        if not errors:
            return None
        return mo.callout(
            mo.md(
                "**Check these values:**\n\n"
                + "\n".join(
                    f"- **{labels.get(field, field.replace('_', ' ').title())}:** {message}"
                    for field, message in errors.items()
                )
            ),
            kind="danger",
        )

    def labeled_group(label, content, class_name=""):
        classes = "ald-scenario-group"
        if class_name:
            classes = f"{classes} {class_name}"
        return mo.Html(
            f"""
            <div class="{classes}">
              <span class="ald-scenario-group-label">{label}</span>
              {content}
            </div>
            """
        )

    def current_structure():
        return scenario_structure.with_rows(scenario_rows)

    def remove_handler(scenario_id):
        return lambda _: set_scenario_editor_state(current_structure().remove_scenario(scenario_id))

    scenario_row_views = []
    scenario_remove_buttons = {}
    can_remove_scenarios = len(scenario_rows) > 1
    for _index, (_scenario_key, _row) in enumerate(
        zip(scenario_keys, scenario_rows, strict=True), start=1
    ):
        _scenario_id = scenario_id_by_key[_scenario_key]
        controls = scenario_forms[_scenario_key]
        _scenario = Scenario.from_dict(_row)

        identity_items = [controls["name"]]
        if not str(_row["name"]).strip():
            identity_items.append(
                mo.callout("Give this scenario a name before calculating.", kind="danger")
            )
        row_groups = [
            labeled_group(
                f"Scenario {_index}",
                mo.vstack(identity_items, gap=0.5),
            )
        ]

        frequency_method = str(_row["frequency_method"])
        frequency_inputs = [
            controls[f"frequency_{field}"] for field in frequency_parameter_fields(frequency_method)
        ]
        frequency_items = [
            controls["frequency_method"],
            mo.hstack(
                frequency_inputs,
                justify="start",
                align="end",
                wrap=True,
                gap=0.75,
                widths="equal",
            ),
        ]
        frequency_validation = validation_message(
            validate_params(
                "frequency",
                _scenario.frequency_method,
                _scenario.frequency_params,
            ),
            frequency_field_labels,
        )
        if frequency_validation is not None:
            frequency_items.append(frequency_validation)
        row_groups.append(labeled_group("Frequency", mo.vstack(frequency_items, gap=0.75)))

        cost_method = str(_row["cost_dist_type"])
        cost_inputs = [controls[f"cost_{field}"] for field in cost_parameter_fields(cost_method)]
        cost_items = [
            controls["cost_dist_type"],
            mo.hstack(
                cost_inputs,
                justify="start",
                align="end",
                wrap=True,
                gap=0.75,
                widths="equal",
            ),
        ]
        cost_validation = validation_message(
            validate_params(
                "cost",
                _scenario.cost_dist_type,
                _scenario.cost_params,
            ),
            cost_field_labels,
        )
        if cost_validation is not None:
            cost_items.append(cost_validation)
        row_groups.append(labeled_group("Cost", mo.vstack(cost_items, gap=0.75)))

        if can_remove_scenarios:
            remove_scenario_button = mo.ui.button(
                label="Remove",
                kind="danger",
                tooltip=f"Remove scenario {_index}",
                on_click=remove_handler(_scenario_id),
            )
            scenario_remove_buttons[_scenario_id] = remove_scenario_button
            row_groups.append(
                labeled_group(
                    "Actions",
                    remove_scenario_button,
                    "ald-scenario-actions",
                )
            )
        scenario_row_class = "ald-scenario-row ald-scenario-row--two-models"
        if can_remove_scenarios:
            scenario_row_class += " ald-scenario-row--with-actions"
        scenario_row_views.append(
            mo.Html(
                f"""
                <article class="{scenario_row_class}" role="listitem">
                  {"".join(group.text for group in row_groups)}
                </article>
                """
            )
        )

    add_scenario_button = mo.ui.button(
        label="Add scenario",
        kind="success",
        tooltip="Append a scenario with safe starting values",
        on_click=lambda _: set_scenario_editor_state(current_structure().add_scenario()),
    )
    # Keep the UIElement objects strongly referenced: the raw HTML below only owns
    # their markup, while Marimo's UI registry itself stores weak references.
    scenario_actions = {
        "add": add_scenario_button,
        "remove": scenario_remove_buttons,
    }
    scenario_list = mo.Html(
        f'<div class="ald-scenario-list" role="list">'
        f"{''.join(view.text for view in scenario_row_views)}</div>"
    )

    scenario_section = surface(
        mo.vstack(
            [
                panel_heading(
                    "Shared threat scenarios",
                    "Each row pairs its frequency with its cost; annual losses sum across all rows.",
                ),
                scenario_list,
                mo.hstack(
                    [
                        mo.md(
                            f"*{len(scenario_rows)} "
                            f"scenario{'s' if len(scenario_rows) != 1 else ''} "
                            "in this local session.*"
                        ),
                        add_scenario_button,
                    ],
                    justify="space-between",
                    align="center",
                    wrap=True,
                    gap=0.75,
                ),
            ],
            gap=1,
        ),
        "ald-input-card ald-scenario-editor",
    )
    return scenario_actions, scenario_rows, scenario_section


@app.cell(hide_code=True)
def _(
    Scenario,
    average_panel_params,
    cost_distribution,
    cost_mode,
    cost_panel_rows,
    cost_parameters,
    frequency_distribution,
    frequency_mode,
    frequency_panel_rows,
    frequency_parameters,
    parameter_fields,
    scenario_mode,
    scenario_rows,
    simulation_seed,
    validate_params,
):
    def resolve_section(section, mode, distribution, direct_editor, panel_rows):
        direct_values = dict(direct_editor.value)
        errors = []
        if mode == "panel":
            if len(panel_rows) < 2:
                errors.append(f"{section.title()} panel requires at least two experts.")
                effective = direct_values
            else:
                fields = parameter_fields(distribution)
                for index, row in enumerate(panel_rows, start=1):
                    row_errors = validate_params(section, distribution, row)
                    errors.extend(
                        f"{section.title()} panel row {index} · {field}: {message}"
                        for field, message in row_errors.items()
                    )
                try:
                    effective = average_panel_params(panel_rows, fields=fields)
                except (TypeError, ValueError) as error:
                    errors.append(f"{section.title()} panel: {error}")
                    effective = direct_values
        else:
            effective = direct_values

        if mode != "scenario":
            field_errors = validate_params(section, distribution, effective)
            errors.extend(
                f"{section.title()} · {field}: {message}" for field, message in field_errors.items()
            )
        return effective, panel_rows, errors

    frequency_params, frequency_panelists, frequency_errors = resolve_section(
        "frequency",
        frequency_mode.value,
        frequency_distribution.value,
        frequency_parameters,
        frequency_panel_rows,
    )
    cost_params, cost_panelists, cost_errors = resolve_section(
        "cost",
        cost_mode.value,
        cost_distribution.value,
        cost_parameters,
        cost_panel_rows,
    )

    scenarios = []
    scenario_common_errors = []
    scenario_frequency_errors = []
    scenario_cost_errors = []
    if scenario_mode:
        if not scenario_rows:
            scenario_common_errors.append("At least one threat scenario is required.")
        for index, row in enumerate(scenario_rows, start=1):
            try:
                scenario = Scenario.from_dict(row)
                scenarios.append(scenario)
                if not scenario.name.strip():
                    scenario_common_errors.append(f"Scenario row {index} needs a name.")
                row_errors = validate_params(
                    "frequency",
                    scenario.frequency_method,
                    scenario.frequency_params,
                )
                scenario_frequency_errors.extend(
                    f"Scenario {index} frequency · {field}: {message}"
                    for field, message in row_errors.items()
                )
                row_errors = validate_params("cost", scenario.cost_dist_type, scenario.cost_params)
                scenario_cost_errors.extend(
                    f"Scenario {index} cost · {field}: {message}"
                    for field, message in row_errors.items()
                )
            except (TypeError, ValueError) as error:
                scenario_common_errors.append(f"Scenario row {index}: {error}")

    _seed_value = simulation_seed.value
    seed_errors = []
    if (
        isinstance(_seed_value, bool)
        or not isinstance(_seed_value, (int, float))
        or _seed_value < 0
        or not float(_seed_value).is_integer()
    ):
        seed_errors.append("Reproducibility seed must be a non-negative integer.")

    frequency_preview_model_errors = (
        frequency_errors + scenario_common_errors + scenario_frequency_errors + seed_errors
    )
    cost_preview_model_errors = (
        cost_errors
        + scenario_common_errors
        + scenario_frequency_errors
        + scenario_cost_errors
        + seed_errors
    )
    model_errors = (
        frequency_errors
        + cost_errors
        + scenario_common_errors
        + scenario_frequency_errors
        + scenario_cost_errors
        + seed_errors
    )
    return (
        cost_preview_model_errors,
        cost_panelists,
        cost_params,
        frequency_preview_model_errors,
        frequency_panelists,
        frequency_params,
        model_errors,
        scenario_rows,
        scenarios,
    )


@app.cell(hide_code=True)
def _(
    EmpiricalCDF,
    SimulationConfig,
    cost_distribution,
    cost_params,
    cost_preview_model_errors,
    distribution_curve,
    frequency_distribution,
    frequency_params,
    frequency_preview_model_errors,
    scenario_mode,
    scenarios,
    simulation_seed,
    simulate_scenarios,
):
    frequency_chart_data = None
    frequency_report_data = None
    cost_chart_data = None
    cost_report_data = None
    preview_errors = []

    if not frequency_preview_model_errors:
        try:
            if scenario_mode:
                frequency_chart_data = simulate_scenarios(
                    scenarios,
                    "frequency",
                    config=SimulationConfig(seed=int(simulation_seed.value), rounds=10_000),
                )
                frequency_report_data = frequency_chart_data
            else:
                frequency_chart_data = distribution_curve(
                    frequency_distribution.value, frequency_params
                )
                frequency_report_data = EmpiricalCDF(
                    frequency_chart_data.x, frequency_chart_data.cdf
                )
        except (ArithmeticError, TypeError, ValueError) as error:
            preview_errors.append(f"Frequency preview: {error}")

    if not cost_preview_model_errors:
        try:
            if scenario_mode:
                cost_chart_data = simulate_scenarios(
                    scenarios,
                    "cost",
                    config=SimulationConfig(seed=int(simulation_seed.value)),
                )
                cost_report_data = cost_chart_data
            else:
                cost_chart_data = distribution_curve(cost_distribution.value, cost_params)
                cost_report_data = EmpiricalCDF(cost_chart_data.x, cost_chart_data.cdf)
        except (ArithmeticError, TypeError, ValueError) as error:
            preview_errors.append(f"Cost preview: {error}")

    return (
        cost_chart_data,
        cost_report_data,
        frequency_chart_data,
        frequency_report_data,
        preview_errors,
    )


@app.cell(hide_code=True)
def _(
    build_distribution_figure,
    chart_view,
    confidence_level,
    confidence_statement,
    cost_chart_data,
    cost_report_data,
    focus_percentile,
    frequency_chart_data,
    frequency_report_data,
    mo,
):
    def preview_card(chart_data, report_data, section):
        if chart_data is None or report_data is None:
            return mo.callout("Complete valid inputs to render this preview.", kind="warn")
        use_dollars = section != "frequency"
        figure = build_distribution_figure(
            chart_data,
            view=chart_view.value,
            use_dollars=use_dollars,
            section=section,
            focus_percentile=focus_percentile.value / 100,
        )
        statement = confidence_statement(
            report_data,
            section=section,
            confidence_level=confidence_level.value,
        )
        insight = mo.Html(
            f"""
            <div class="ald-insight">
              <strong>Modeled range</strong>
              {statement}
            </div>
            """
        )
        return mo.vstack(
            [
                mo.ui.plotly(figure, config={"displaylogo": False, "responsive": True}),
                insight,
            ],
            gap=1,
        )

    frequency_preview = preview_card(frequency_chart_data, frequency_report_data, "frequency")
    cost_preview = preview_card(cost_chart_data, cost_report_data, "cost")
    return cost_preview, frequency_preview


@app.cell(hide_code=True)
def _(
    DISTRIBUTION_LABELS,
    cost_distribution,
    cost_mode,
    cost_panel,
    cost_panel_rows,
    cost_preview,
    cost_parameters,
    frequency_distribution,
    frequency_mode,
    frequency_panel,
    frequency_panel_rows,
    frequency_preview,
    frequency_parameters,
    format_value,
    mo,
    panel_heading,
    panel_analytics,
    parameter_fields,
    scenario_mode,
    scenario_section,
    section_guidance,
    step_header,
    surface,
):
    def panel_table(rows, distribution, use_dollars):
        try:
            analytics = panel_analytics(rows, fields=parameter_fields(distribution))
            output = []
            for field, stat in analytics.items():

                def formatter(value):
                    return format_value(value, use_dollars=use_dollars)

                output.append(
                    {
                        "Parameter": field,
                        "Average": formatter(stat.average),
                        "Minimum": formatter(stat.minimum),
                        "Maximum": formatter(stat.maximum),
                        "Std. deviation": formatter(stat.stddev),
                    }
                )
            return mo.ui.table(output, selection=None, show_search=False)
        except (TypeError, ValueError) as error:
            return mo.callout(str(error), kind="danger")

    def section_view(
        step,
        section,
        mode,
        distribution,
        parameters,
        panel,
        panel_rows,
        preview,
    ):
        input_items = [
            panel_heading(
                "Model inputs",
                "Choose an elicitation source and shape for this distribution.",
            ),
            mode,
        ]
        if mode.value != "scenario":
            input_items.append(distribution)
        if mode.value == "direct":
            input_items.append(parameters)
        elif mode.value == "panel":
            input_items.extend(
                [
                    mo.md(
                        "Add or delete panelists below. At least two valid expert "
                        "estimates are averaged parameter-by-parameter."
                    ),
                    panel,
                    panel_table(
                        panel_rows,
                        distribution.value,
                        use_dollars=section == "cost",
                    ),
                ]
            )
        else:
            input_items.append(
                mo.callout(
                    "Scenario mode links Frequency and Cost. Configure the paired "
                    "frequency and cost models in the shared editor immediately below.",
                    kind="info",
                )
            )
        preview_label = (
            "Scenario" if mode.value == "scenario" else DISTRIBUTION_LABELS[distribution.value]
        )
        preview_content = mo.vstack(
            [
                panel_heading(
                    f"{preview_label} preview",
                    "Inspect the modeled shape before calculating annual loss.",
                ),
                preview,
            ],
            gap=1,
        )
        section_items = [
            step_header(step, section.title(), section_guidance(section)),
            surface(mo.vstack(input_items, gap=1), "ald-input-card"),
        ]
        if section == "frequency" and scenario_mode:
            section_items.append(scenario_section)
        section_items.append(surface(preview_content, "ald-preview-card"))
        return mo.vstack(section_items, gap=1)

    frequency_section = section_view(
        1,
        "frequency",
        frequency_mode,
        frequency_distribution,
        frequency_parameters,
        frequency_panel,
        frequency_panel_rows,
        frequency_preview,
    )
    cost_section = section_view(
        2,
        "cost",
        cost_mode,
        cost_distribution,
        cost_parameters,
        cost_panel,
        cost_panel_rows,
        cost_preview,
    )
    return cost_section, frequency_section


@app.cell(hide_code=True)
def _(mo):
    get_calculation, set_calculation = mo.state({"result": None, "snapshot": None, "error": None})
    return get_calculation, set_calculation


@app.cell(hide_code=True)
def _(model_errors, mo):
    calculate_button = mo.ui.run_button(
        kind="success",
        disabled=bool(model_errors),
        tooltip=(
            "Resolve validation errors first" if model_errors else "Run annual-loss simulation"
        ),
        label="Calculate / Recalculate annual loss",
        full_width=True,
        keyboard_shortcut="Ctrl-Enter",
    )
    return (calculate_button,)


@app.cell(hide_code=True)
def _(
    AnnualLossError,
    SimulationConfig,
    calculate_button,
    cost_distribution,
    cost_mode,
    cost_panelists,
    cost_params,
    cost_report_data,
    frequency_distribution,
    frequency_mode,
    frequency_panelists,
    frequency_params,
    frequency_report_data,
    model_errors,
    scenario_mode,
    scenarios,
    set_calculation,
    simulate_annual_loss,
    simulate_scenarios,
    simulation_seed,
):
    if calculate_button.value:
        if model_errors:
            set_calculation({"result": None, "snapshot": None, "error": "\n".join(model_errors)})
        else:
            try:
                config = SimulationConfig(seed=int(simulation_seed.value))
                if scenario_mode:
                    loss_result = simulate_scenarios(
                        scenarios,
                        "loss",
                        config=config,
                    )
                else:
                    loss_result = simulate_annual_loss(
                        frequency_distribution.value,
                        frequency_params,
                        cost_distribution.value,
                        cost_params,
                        config=config,
                    )
                _snapshot = {
                    "frequency_params": dict(frequency_params),
                    "cost_params": dict(cost_params),
                    "frequency_distribution": frequency_distribution.value,
                    "cost_distribution": cost_distribution.value,
                    "frequency_result": frequency_report_data,
                    "cost_result": cost_report_data,
                    "scenario_mode": scenario_mode,
                    "scenarios": tuple(scenarios),
                    "frequency_panel_active": frequency_mode.value == "panel",
                    "cost_panel_active": cost_mode.value == "panel",
                    "frequency_panelists": tuple(frequency_panelists),
                    "cost_panelists": tuple(cost_panelists),
                }
                set_calculation({"result": loss_result, "snapshot": _snapshot, "error": None})
            except (AnnualLossError, ArithmeticError, TypeError, ValueError) as error:
                set_calculation({"result": None, "snapshot": None, "error": str(error)})
    return


@app.cell(hide_code=True)
def _(
    build_distribution_figure,
    build_executive_summary,
    chart_view,
    confidence_interval,
    confidence_level,
    copy_button,
    calculate_button,
    focus_percentile,
    format_compact,
    get_calculation,
    mo,
    panel_heading,
    simulation_seed,
    step_header,
    surface,
):
    calculation = get_calculation()
    result = calculation["result"]
    _snapshot = calculation["snapshot"]
    calculation_error = calculation["error"]

    calculate_controls = surface(
        mo.vstack(
            [
                panel_heading(
                    "Simulation run",
                    "Set a seed, then snapshot the current valid inputs.",
                ),
                simulation_seed,
                calculate_button,
            ],
            gap=1,
        ),
        "ald-input-card",
    )
    calculate_items = [
        step_header(
            3,
            "Calculate annual loss",
            "Run the annual model when the inputs look right. Later edits will not change "
            "the result until you explicitly recalculate.",
        ),
        calculate_controls,
    ]

    if calculation_error:
        calculate_items.append(mo.callout(calculation_error, kind="danger"))
    elif result is not None:
        interval = confidence_interval(result, level=confidence_level.value / 100)
        figure = build_distribution_figure(
            result,
            view=chart_view.value,
            use_dollars=True,
            section="loss",
            focus_percentile=focus_percentile.value / 100,
        )
        summary = build_executive_summary(
            **_snapshot,
            loss_result=result,
            confidence_level=confidence_level.value,
        )
        stats = mo.hstack(
            [
                mo.stat(
                    value=format_compact(interval.lower, True),
                    label=f"P{interval.lower_percentile * 100:g} lower bound",
                    caption="Lower edge of the selected modeled range",
                ),
                mo.stat(
                    value=format_compact(interval.median, True),
                    label="P50 median annual loss",
                    caption="Median simulated annual loss",
                ),
                mo.stat(
                    value=format_compact(interval.upper, True),
                    label=f"P{interval.upper_percentile * 100:g} upper bound",
                    caption="Upper edge of the selected modeled range",
                ),
            ],
            justify="space-around",
            wrap=True,
            gap=1,
        )
        report_copy = copy_button(summary.copy_text)
        narrative_items = "".join(
            f"<li>{statement}</li>" for statement in summary.confidence_narrative
        )
        narrative = mo.Html(
            f"""
            <section class="ald-narrative">
              <h3>Modeled outcome ranges</h3>
              <ul>{narrative_items}</ul>
            </section>
            """
        )
        result_chart = surface(
            mo.vstack(
                [
                    mo.ui.plotly(
                        figure,
                        config={"displaylogo": False, "responsive": True},
                    ),
                    mo.md(
                        f"<span class='ald-meta'>Seed **{result.seed:,}** · "
                        f"**{result.num_rounds:,}** simulated years · "
                        f"**{result.total_event_draws:,}** incident-cost draws</span>"
                    ),
                ],
                gap=1,
            ),
            "ald-result-card",
        )
        report_details = mo.accordion(
            {
                "Executive Summary": mo.md(summary.markdown),
            }
        )
        report_row = mo.hstack(
            [report_details, report_copy],
            align="start",
            wrap=True,
            gap=0.5,
            widths=[1, 0],
        )
        calculate_items.extend(
            [
                surface(
                    mo.vstack(
                        [
                            panel_heading(
                                "Decision range",
                                "Central modeled annual-loss outcomes.",
                            ),
                            stats,
                        ],
                        gap=1,
                    ),
                    "ald-result-card",
                ),
                result_chart,
                narrative,
                surface(report_row, "ald-report-card"),
            ]
        )

    calculate_section = mo.vstack(calculate_items, gap=1)
    return (calculate_section,)


@app.cell(hide_code=True)
def _(
    calculate_section,
    cost_section,
    frequency_section,
    mo,
    model_errors,
    preview_errors,
    view_controls,
):
    feedback = []
    all_errors = list(model_errors) + list(preview_errors)
    if all_errors:
        feedback.append(
            mo.callout(
                mo.md(
                    "**Resolve these inputs before calculating:**\n\n"
                    + "\n".join(f"- {error}" for error in all_errors)
                ),
                kind="danger",
            )
        )

    main_items = [
        view_controls,
        *feedback,
        frequency_section,
        cost_section,
        calculate_section,
    ]
    main_content = mo.vstack(main_items, gap=1.5)
    mo.Html(f'<main class="ald-shell">{main_content}</main>')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html(
        """
        <footer class="ald-footer">This tool models elicited assumptions; it is not a forecast,
        accounting opinion, or substitute for professional risk judgment. All inputs and
        calculations remain in this local Marimo session.</footer>
        """
    )
    return


if __name__ == "__main__":
    app.run()
