import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full", app_title="Annual Loss Distribution")


@app.cell(hide_code=True)
def _():
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
    from annual_loss.reporting import (
        build_executive_summary,
        confidence_statement,
        section_guidance,
    )

    return (
        DEFAULT_SCENARIOS,
        AnnualLossError,
        EmpiricalCDF,
        Mapping,
        Scenario,
        SimulationConfig,
        asdict,
        average_panel_params,
        build_distribution_figure,
        build_executive_summary,
        confidence_interval,
        confidence_statement,
        distribution_curve,
        format_compact,
        format_value,
        is_dataclass,
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

    return (
        DEFAULT_PARAMETERS,
        DEFAULT_SCENARIO_ROWS,
        DISTRIBUTION_LABELS,
        DISTRIBUTION_OPTIONS,
        MODE_OPTIONS,
        PARAMETER_LABELS,
        parameter_defaults,
        parameter_fields,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.Html(
        """
        <style>
          :root { --ald-accent: #4361ee; --ald-pink: #f72585; }
          .ald-hero { padding: 1.5rem 0 0.5rem; text-align: center; }
          .ald-hero h1 { margin-bottom: .25rem; letter-spacing: -.03em; }
          .ald-hero p { color: var(--muted-foreground); margin: 0 auto; max-width: 50rem; }
          .ald-note { color: var(--muted-foreground); font-size: .9rem; }
          .ald-meta { color: var(--muted-foreground); font-size: .85rem; }
        </style>
        <div class="ald-hero">
          <h1>Eliciting an Annual Loss Distribution</h1>
          <p>Turn security-risk estimates into reproducible frequency, cost, and annual-loss
          distributions with trusted Python numerical libraries.</p>
        </div>
        """
    )
    return


@app.cell(hide_code=True)
def _(DISTRIBUTION_OPTIONS, MODE_OPTIONS, mo):
    frequency_mode = mo.ui.radio(
        MODE_OPTIONS,
        value="Direct estimate",
        inline=True,
        label="Frequency input source",
    )
    frequency_distribution = mo.ui.dropdown(
        DISTRIBUTION_OPTIONS,
        value="Lognormal",
        label="Frequency distribution",
    )
    cost_mode = mo.ui.radio(
        MODE_OPTIONS,
        value="Direct estimate",
        inline=True,
        label="Cost input source",
    )
    cost_distribution = mo.ui.dropdown(
        DISTRIBUTION_OPTIONS,
        value="Lognormal",
        label="Cost distribution",
    )
    chart_view = mo.ui.radio(
        {"PDF / histogram": "pdf", "CDF": "cdf"},
        value="PDF / histogram",
        inline=True,
        label="Chart view",
    )
    focus_percentile = mo.ui.slider(
        start=95.0,
        stop=99.9,
        step=0.1,
        value=99.5,
        show_value=True,
        label="Show outcomes through percentile",
    )
    confidence_level = mo.ui.slider(
        start=50,
        stop=95,
        step=1,
        value=90,
        show_value=True,
        label="Central modeled outcome range",
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
        cost_mode,
        focus_percentile,
        frequency_distribution,
        frequency_mode,
        simulation_seed,
    )


@app.cell(hide_code=True)
def _(
    PARAMETER_LABELS,
    cost_distribution,
    frequency_distribution,
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

    frequency_parameters = make_parameter_editor("frequency", frequency_distribution.value)
    cost_parameters = make_parameter_editor("cost", cost_distribution.value)
    return cost_parameters, frequency_parameters


@app.cell(hide_code=True)
def _(
    PARAMETER_LABELS,
    cost_distribution,
    frequency_distribution,
    mo,
    parameter_defaults,
    parameter_fields,
):
    def make_panel_editor(section, distribution):
        defaults = parameter_defaults(section, distribution)
        fields = parameter_fields(distribution)
        rows = [
            {"name": f"Panelist {index}", **{field: defaults[field] for field in fields}}
            for index in (1, 2)
        ]
        return mo.ui.data_editor(
            rows,
            label=f"{section.title()} expert estimates",
            editable_columns="all",
        )

    frequency_panel = make_panel_editor("frequency", frequency_distribution.value)
    cost_panel = make_panel_editor("cost", cost_distribution.value)
    return cost_panel, frequency_panel


@app.cell(hide_code=True)
def _(DEFAULT_SCENARIO_ROWS, mo):
    scenario_editor = mo.ui.data_editor(
        DEFAULT_SCENARIO_ROWS,
        label="Threat scenarios",
        editable_columns="all",
    )
    return (scenario_editor,)


@app.cell(hide_code=True)
def _(
    Scenario,
    average_panel_params,
    cost_distribution,
    cost_mode,
    cost_panel,
    cost_parameters,
    frequency_distribution,
    frequency_mode,
    frequency_panel,
    frequency_parameters,
    parameter_fields,
    scenario_editor,
    simulation_seed,
    validate_params,
):
    def records(value):
        if value is None:
            return []
        if hasattr(value, "to_dict") and not isinstance(value, dict):
            try:
                return value.to_dict(orient="records")
            except TypeError:
                return value.to_dict("records")
        if isinstance(value, dict):
            if not value:
                return []
            keys = list(value)
            return [
                dict(zip(keys, row, strict=True))
                for row in zip(*(value[k] for k in keys), strict=True)
            ]
        return [dict(row) for row in value]

    def resolve_section(section, mode, distribution, direct_editor, panel_editor):
        direct_values = dict(direct_editor.value)
        panel_rows = records(panel_editor.value)
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
        frequency_panel,
    )
    cost_params, cost_panelists, cost_errors = resolve_section(
        "cost",
        cost_mode.value,
        cost_distribution.value,
        cost_parameters,
        cost_panel,
    )

    scenario_rows = records(scenario_editor.value)
    scenarios = []
    scenario_errors = []
    frequency_scenario_mode = frequency_mode.value == "scenario"
    cost_scenario_mode = cost_mode.value == "scenario"
    if frequency_scenario_mode or cost_scenario_mode:
        if not scenario_rows:
            scenario_errors.append("At least one threat scenario is required.")
        for index, row in enumerate(scenario_rows, start=1):
            try:
                scenario = Scenario.from_dict(row)
                scenarios.append(scenario)
                if not scenario.name.strip():
                    scenario_errors.append(f"Scenario row {index} needs a name.")
                if frequency_scenario_mode:
                    row_errors = validate_params(
                        "frequency",
                        scenario.frequency_method,
                        scenario.frequency_params,
                    )
                    scenario_errors.extend(
                        f"Scenario {index} frequency · {field}: {message}"
                        for field, message in row_errors.items()
                    )
                if cost_scenario_mode:
                    row_errors = validate_params(
                        "cost", scenario.cost_dist_type, scenario.cost_params
                    )
                    scenario_errors.extend(
                        f"Scenario {index} cost · {field}: {message}"
                        for field, message in row_errors.items()
                    )
            except (TypeError, ValueError) as error:
                scenario_errors.append(f"Scenario row {index}: {error}")

    _seed_value = simulation_seed.value
    seed_errors = []
    if (
        isinstance(_seed_value, bool)
        or not isinstance(_seed_value, (int, float))
        or _seed_value < 0
        or not float(_seed_value).is_integer()
    ):
        seed_errors.append("Reproducibility seed must be a non-negative integer.")

    model_errors = frequency_errors + cost_errors + scenario_errors + seed_errors
    return (
        cost_panelists,
        cost_params,
        cost_scenario_mode,
        frequency_panelists,
        frequency_params,
        frequency_scenario_mode,
        model_errors,
        records,
        scenario_rows,
        scenarios,
    )


@app.cell(hide_code=True)
def _(
    EmpiricalCDF,
    SimulationConfig,
    cost_distribution,
    cost_params,
    cost_scenario_mode,
    distribution_curve,
    frequency_distribution,
    frequency_params,
    frequency_scenario_mode,
    model_errors,
    scenarios,
    simulation_seed,
    simulate_scenarios,
):
    frequency_chart_data = None
    frequency_report_data = None
    cost_chart_data = None
    cost_report_data = None
    preview_errors = []

    if not model_errors:
        try:
            if frequency_scenario_mode:
                frequency_chart_data = simulate_scenarios(
                    scenarios,
                    "frequency",
                    frequency_scenario_mode=True,
                    cost_scenario_mode=cost_scenario_mode,
                    frequency_dist_type=frequency_distribution.value,
                    frequency_params=frequency_params,
                    cost_dist_type=cost_distribution.value,
                    cost_params=cost_params,
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

            if cost_scenario_mode:
                cost_chart_data = simulate_scenarios(
                    scenarios,
                    "cost",
                    frequency_scenario_mode=frequency_scenario_mode,
                    cost_scenario_mode=True,
                    frequency_dist_type=frequency_distribution.value,
                    frequency_params=frequency_params,
                    cost_dist_type=cost_distribution.value,
                    cost_params=cost_params,
                    config=SimulationConfig(seed=int(simulation_seed.value), rounds=10_000),
                )
                cost_report_data = cost_chart_data
            else:
                cost_chart_data = distribution_curve(cost_distribution.value, cost_params)
                cost_report_data = EmpiricalCDF(cost_chart_data.x, cost_chart_data.cdf)
        except (ArithmeticError, TypeError, ValueError) as error:
            preview_errors.append(str(error))

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
        return mo.vstack([mo.ui.plotly(figure), mo.callout(statement, kind="neutral")], gap=1)

    frequency_preview = preview_card(frequency_chart_data, frequency_report_data, "frequency")
    cost_preview = preview_card(cost_chart_data, cost_report_data, "cost")
    return cost_preview, frequency_preview


@app.cell(hide_code=True)
def _(
    DISTRIBUTION_LABELS,
    cost_distribution,
    cost_mode,
    cost_panel,
    cost_preview,
    cost_parameters,
    frequency_distribution,
    frequency_mode,
    frequency_panel,
    frequency_preview,
    frequency_parameters,
    format_value,
    mo,
    panel_analytics,
    parameter_fields,
    records,
    section_guidance,
):
    def panel_table(editor, distribution, use_dollars):
        rows = records(editor.value)
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

    def section_view(section, mode, distribution, parameters, panel, preview):
        items = [
            mo.md(f"## {section.title()}"),
            mo.md(section_guidance(section)),
            mode,
        ]
        if mode.value != "scenario":
            items.append(distribution)
        if mode.value == "direct":
            items.append(parameters)
        elif mode.value == "panel":
            items.extend(
                [
                    mo.md(
                        "Add or remove rows in the editor. At least two valid expert "
                        "estimates are averaged parameter-by-parameter."
                    ),
                    panel,
                    panel_table(
                        panel,
                        distribution.value,
                        use_dollars=section == "cost",
                    ),
                ]
            )
        else:
            items.append(
                mo.callout(
                    "This section is driven by the shared scenario editor below.",
                    kind="info",
                )
            )
        preview_label = (
            "Scenario" if mode.value == "scenario" else DISTRIBUTION_LABELS[distribution.value]
        )
        items.extend(
            [
                mo.md(f"### {preview_label} preview"),
                preview,
            ]
        )
        return mo.vstack(items, gap=1)

    frequency_section = section_view(
        "frequency",
        frequency_mode,
        frequency_distribution,
        frequency_parameters,
        frequency_panel,
        frequency_preview,
    )
    cost_section = section_view(
        "cost",
        cost_mode,
        cost_distribution,
        cost_parameters,
        cost_panel,
        cost_preview,
    )
    return cost_section, frequency_section


@app.cell(hide_code=True)
def _(
    cost_scenario_mode,
    frequency_scenario_mode,
    mo,
    scenario_editor,
):
    if frequency_scenario_mode or cost_scenario_mode:
        scenario_section = mo.vstack(
            [
                mo.md("## Shared threat scenarios"),
                mo.md(
                    "Edit, add, or remove rows. `frequency_method` accepts `odds`, "
                    "`lognormal`, `pert`, or `pareto`; `cost_dist_type` accepts "
                    "`lognormal`, `pert`, or `pareto`. Only the parameter columns for "
                    "each selected method are used."
                ),
                scenario_editor,
            ],
            gap=1,
        )
    else:
        scenario_section = mo.callout(
            "Choose Threat scenarios for Frequency or Cost to open the shared editor.",
            kind="neutral",
        )
    return (scenario_section,)


@app.cell(hide_code=True)
def _(mo):
    get_calculation, set_calculation = mo.state({"result": None, "snapshot": None, "error": None})
    return get_calculation, set_calculation


@app.cell(hide_code=True)
def _(mo):
    get_active_workflow_tab, set_active_workflow_tab = mo.state("1 · Frequency")
    return get_active_workflow_tab, set_active_workflow_tab


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
    cost_scenario_mode,
    frequency_distribution,
    frequency_mode,
    frequency_panelists,
    frequency_params,
    frequency_report_data,
    frequency_scenario_mode,
    model_errors,
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
                if frequency_scenario_mode or cost_scenario_mode:
                    loss_result = simulate_scenarios(
                        scenarios,
                        "loss",
                        frequency_scenario_mode=frequency_scenario_mode,
                        cost_scenario_mode=cost_scenario_mode,
                        frequency_dist_type=frequency_distribution.value,
                        frequency_params=frequency_params,
                        cost_dist_type=cost_distribution.value,
                        cost_params=cost_params,
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
                    "frequency_scenario_mode": frequency_scenario_mode,
                    "cost_scenario_mode": cost_scenario_mode,
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
    calculate_button,
    focus_percentile,
    format_compact,
    get_calculation,
    mo,
    simulation_seed,
):
    calculation = get_calculation()
    result = calculation["result"]
    _snapshot = calculation["snapshot"]
    calculation_error = calculation["error"]

    calculate_items = [
        mo.md("## Calculate annual loss"),
        mo.md(
            "This step snapshots the current valid inputs. Later edits do not change the "
            "existing result until you explicitly recalculate."
        ),
        simulation_seed,
        calculate_button,
    ]

    if calculation_error:
        calculate_items.append(mo.callout(calculation_error, kind="danger"))
    elif result is None:
        calculate_items.append(
            mo.callout(
                "Configure Frequency and Cost, then calculate the annual-loss distribution.",
                kind="info",
            )
        )
    else:
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
                    bordered=True,
                ),
                mo.stat(
                    value=format_compact(interval.median, True),
                    label="P50 median annual loss",
                    bordered=True,
                ),
                mo.stat(
                    value=format_compact(interval.upper, True),
                    label=f"P{interval.upper_percentile * 100:g} upper bound",
                    bordered=True,
                ),
            ],
            justify="space-around",
            gap=1,
        )
        report_copy = mo.ui.code_editor(
            value=summary.copy_text,
            language="text",
            disabled=True,
            min_height=260,
            max_height=520,
            show_copy_button=True,
            label="Copy-ready executive report",
        )
        report_download = mo.download(
            lambda: summary.copy_text,
            filename="annual-loss-executive-summary.txt",
            mimetype="text/plain",
            label="Download report",
        )
        calculate_items.extend(
            [
                mo.md("### Annual loss distribution"),
                stats,
                mo.ui.plotly(figure),
                mo.md(
                    f"<span class='ald-meta'>Seed **{result.seed:,}** · "
                    f"**{result.num_rounds:,}** simulated years · "
                    f"**{result.total_event_draws:,}** incident-cost draws</span>"
                ),
                mo.md(summary.markdown),
                report_copy,
                report_download,
            ]
        )

    calculate_section = mo.vstack(calculate_items, gap=1)
    return (calculate_section,)


@app.cell(hide_code=True)
def _(
    calculate_section,
    chart_view,
    confidence_level,
    cost_section,
    focus_percentile,
    frequency_section,
    get_active_workflow_tab,
    mo,
    model_errors,
    preview_errors,
    scenario_section,
    set_active_workflow_tab,
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

    global_controls = mo.hstack(
        [chart_view, focus_percentile, confidence_level],
        justify="start",
        align="end",
        wrap=True,
        gap=2,
    )
    _tab_contents = {
        "1 · Frequency": frequency_section,
        "2 · Cost": cost_section,
        "3 · Calculate": calculate_section,
    }
    _active_tab = get_active_workflow_tab()
    if _active_tab not in _tab_contents:
        _active_tab = "1 · Frequency"
    workflow = mo.ui.tabs(
        _tab_contents,
        value=_active_tab,
        lazy=False,
        label="Annual loss workflow",
        on_change=set_active_workflow_tab,
    )
    mo.vstack(
        [global_controls, *feedback, workflow, scenario_section],
        gap=1.5,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html(
        """
        <hr>
        <p class="ald-note">This tool models elicited assumptions; it is not a forecast,
        accounting opinion, or substitute for professional risk judgment. All inputs and
        calculations remain in this local Marimo session.</p>
        """
    )
    return


if __name__ == "__main__":
    app.run()
