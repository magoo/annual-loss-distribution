"""Validated snapshots and presentation payloads for the persistent editor."""

from __future__ import annotations

import json
from copy import deepcopy

from .analysis_document import active_fields, parameter_fields, row_key, validate_document
from .charts import build_distribution_figure
from .distributions import distribution_curve
from .formatting import format_compact, format_value
from .models import EmpiricalCDF, Scenario, SimulationConfig
from .reporting import build_executive_summary, confidence_statement
from .simulation import simulate_annual_loss, simulate_scenarios
from .statistics import average_panel_params, confidence_interval, panel_analytics
from .validation import validate_params


def resolve_document(document):
    """Resolve only active inputs, with errors addressed by stable field path."""
    doc = validate_document(document)
    active = active_fields(doc)
    errors = {
        path: "Finish this field with Enter or by leaving it. Your typing is saved."
        for path in doc["drafts"]
        if path in active
    }
    scenario_mode = doc["workflow"]["frequency_mode"] == "scenario"
    resolved = {"scenario_mode": scenario_mode, "scenarios": (), "seed": int(doc["seed"])}
    for section in ("frequency", "cost"):
        source = doc[section]
        distribution = source["distribution"]
        panel_active = doc["workflow"][section + "_mode"] == "panel"
        params = dict(source["direct"][distribution])
        rows = deepcopy(source["panel"]["rows"])
        if not scenario_mode:
            if panel_active:
                for row in rows:
                    errors.update(
                        {
                            f"{section}:panel:{int(row['id'])}:{field}": message
                            for field, message in validate_params(
                                section, distribution, row
                            ).items()
                        }
                    )
                params = average_panel_params(rows, fields=parameter_fields(distribution))
            errors.update(
                {
                    f"{section}:direct:{distribution}:{field}"
                    if not panel_active
                    else f"{section}:panel:{field}": message
                    for field, message in validate_params(section, distribution, params).items()
                }
            )
        resolved.update(
            {
                section + "_distribution": distribution,
                section + "_params": params,
                section + "_panel_active": panel_active,
                section + "_panelists": tuple(rows),
            }
        )
    if scenario_mode:
        scenarios = []
        for row in doc["scenarios"]["rows"]:
            prefix = f"scenario:{row_key(row['id'])}:"
            if not row["name"].strip():
                errors[prefix + "name"] = "Give this scenario a name before calculating."
            scenario = Scenario.from_dict(row)
            scenarios.append(scenario)
            for section, method, params in (
                ("frequency", scenario.frequency_method, scenario.frequency_params),
                ("cost", scenario.cost_dist_type, scenario.cost_params),
            ):
                errors.update(
                    {
                        prefix + section + "_" + field: message
                        for field, message in validate_params(section, method, params).items()
                    }
                )
        resolved["scenarios"] = tuple(scenarios)
    return errors, resolved


def preview_allowed(section, scenario_mode, errors):
    for path in errors:
        if path in ("seed", "model") or path.startswith(section + ":"):
            return False
        if scenario_mode and path.startswith("scenario:"):
            field = path.rsplit(":", 1)[-1]
            if field == "name" or field.startswith("frequency_") or section == "cost":
                return False
    return True


def preview_models(resolved, sections=("frequency", "cost")):
    data = {}
    for section in sections:
        if resolved["scenario_mode"]:
            model = simulate_scenarios(
                resolved["scenarios"],
                section,
                config=SimulationConfig(
                    seed=resolved["seed"], rounds=10_000 if section == "frequency" else None
                ),
            )
            report = model
        else:
            model = distribution_curve(
                resolved[section + "_distribution"], resolved[section + "_params"]
            )
            report = EmpiricalCDF(model.x, model.cdf)
        data[section] = (model, report)
    return data


def chart_payload(model, view, section):
    figure = build_distribution_figure(
        model,
        view=view["chart"],
        use_dollars=section != "frequency",
        section=section,
        focus_percentile=view["focus_percentile"] / 100,
    )
    return json.loads(figure.to_json())


def render_result(result, snapshot, view):
    interval = confidence_interval(result, level=view["confidence_level"] / 100)
    summary = build_executive_summary(
        **snapshot, loss_result=result, confidence_level=view["confidence_level"]
    )
    return {
        "figure": chart_payload(result, view, "loss"),
        "stats": [
            {
                "label": f"P{interval.lower_percentile * 100:g} lower bound",
                "value": format_compact(interval.lower, True),
            },
            {"label": "P50 median annual loss", "value": format_compact(interval.median, True)},
            {
                "label": f"P{interval.upper_percentile * 100:g} upper bound",
                "value": format_compact(interval.upper, True),
            },
        ],
        "meta": f"Seed {result.seed:,} · {result.num_rounds:,} simulated years · {result.total_event_draws:,} incident-cost draws",
        "summary": summary.copy_text,
        "narrative": list(summary.confidence_narrative),
    }


class AnalysisSession:
    """Ephemeral results for one activation; request retries never resimulate.

    Browser edits are authoritative. This object owns only derived Python data,
    receives explicit immutable requests, and is never serialized in a backup.
    """

    def __init__(self):
        self.activation = None
        self.last_token = None
        self.last_response = None
        self.result = None
        self.snapshot = None
        self.preview_key = None
        self.previews = None

    def process(self, request):
        if not request:
            return {}
        identity = (request.get("analysis", {}).get("id"), request.get("activation"))
        token = request.get("token")
        if not all(isinstance(item, str) and item for item in (*identity, token)):
            raise ValueError("Invalid analysis request identity")
        if request.get("action") not in ("preview", "calculate", "view"):
            raise ValueError("Unsupported analysis action")
        if identity == self.activation and token == self.last_token:
            return deepcopy(self.last_response)
        if identity != self.activation:
            self.result = self.snapshot = self.previews = self.preview_key = None
            self.activation = identity
        doc = deepcopy(request["analysis"])
        response = {
            "analysis_id": identity[0],
            "activation": identity[1],
            "token": token,
            "action": request["action"],
            "errors": {},
            "previews": {},
            "panels": {},
            "loss": None,
        }
        try:
            errors, resolved = resolve_document(doc)
            response["errors"] = errors
            # Each preview keeps the original independent validation boundary.
            # Scenario cost sampling needs valid frequencies, but an unfinished
            # cost estimate does not prevent a frequency-only preview.
            key = {key: value for key, value in resolved.items() if not key.endswith("panelists")}
            if key != self.preview_key:
                self.previews = {}
                self.preview_key = deepcopy(key)
            for section in ("frequency", "cost"):
                if not preview_allowed(section, resolved["scenario_mode"], errors):
                    continue
                try:
                    if section not in self.previews:
                        self.previews.update(preview_models(resolved, (section,)))
                    model, report = self.previews[section]
                    response["previews"][section] = {
                        "figure": chart_payload(model, doc["view"], section),
                        "statement": confidence_statement(
                            report,
                            section=section,
                            confidence_level=doc["view"]["confidence_level"],
                        ),
                    }
                except (ArithmeticError, TypeError, ValueError) as error:
                    errors[section + ":preview"] = str(error)
            if not errors:
                if request["action"] == "calculate":
                    config = SimulationConfig(seed=resolved["seed"])
                    result = (
                        simulate_scenarios(resolved["scenarios"], "loss", config=config)
                        if resolved["scenario_mode"]
                        else simulate_annual_loss(
                            resolved["frequency_distribution"],
                            resolved["frequency_params"],
                            resolved["cost_distribution"],
                            resolved["cost_params"],
                            config=config,
                        )
                    )
                    snapshot = {key: value for key, value in resolved.items() if key != "seed"}
                    snapshot.update(
                        {
                            section + "_result": self.previews[section][1]
                            for section in ("frequency", "cost")
                        }
                    )
                    self.result, self.snapshot = result, snapshot
            for section in ("frequency", "cost"):
                if doc["workflow"][section + "_mode"] == "panel":
                    stats = panel_analytics(
                        doc[section]["panel"]["rows"],
                        fields=parameter_fields(doc[section]["distribution"]),
                    )
                    response["panels"][section] = [
                        {
                            "Parameter": field,
                            **{
                                label: format_value(
                                    getattr(stat, attr), use_dollars=section == "cost"
                                )
                                for label, attr in (
                                    ("Average", "average"),
                                    ("Minimum", "minimum"),
                                    ("Maximum", "maximum"),
                                    ("Std. deviation", "stddev"),
                                )
                            },
                        }
                        for field, stat in stats.items()
                    ]
            if self.result is not None:
                response["loss"] = render_result(self.result, self.snapshot, doc["view"])
        except (ArithmeticError, TypeError, ValueError, KeyError) as error:
            response["errors"]["model"] = str(error)
        self.last_token, self.last_response = token, deepcopy(response)
        return response
