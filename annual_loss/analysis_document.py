"""Portable analysis documents, independent of Marimo and browser storage.

Document validation checks recoverability. Model validation is deliberately a
separate operation: an unfinished or out-of-order estimate is still worth saving.
"""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from uuid import uuid4

from .models import DEFAULT_SCENARIOS
from .panel_editor import PanelEditorState
from .scenario_editor import ScenarioEditorState
from .workflow_state import WorkflowModeState

FORMAT = "security-annual-loss-analysis"
LIBRARY_FORMAT = "security-annual-loss-library"
VERSION = MODEL_VERSION = 1
MAX_BACKUP_BYTES = 10 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1
DISTRIBUTIONS = ("lognormal", "pert", "pareto")
FIELDS = ("p50", "p95", "min", "mode", "max")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,100}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    require(
        isinstance(value, dict) and set(value) == set(expected),
        f"{label}: unexpected or missing fields",
    )


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def safe_integer(value, minimum=0):
    return number(value) and minimum <= value <= MAX_SAFE_INTEGER and value == int(value)


def row_key(value):
    return f"string:{value}" if isinstance(value, str) else f"integer:{int(value)}"


def parameter_fields(distribution):
    return (
        ("min", "mode", "max")
        if distribution == "pert"
        else (("odds",) if distribution == "odds" else ("p50", "p95"))
    )


def parameter_defaults(section):
    return dict(
        zip(
            FIELDS,
            (1.0, 10.0, 0.0, 1.0, 10.0)
            if section == "frequency"
            else (50_000.0, 500_000.0, 1_000.0, 50_000.0, 500_000.0),
            strict=True,
        )
    )


def editable_fields(doc):
    """Map stable draft paths to (containing object, field, numeric)."""
    fields = {"seed": (doc, "seed", True)}
    for section in ("frequency", "cost"):
        source = doc[section]
        for distribution, params in source["direct"].items():
            for field in params:
                fields[f"{section}:direct:{distribution}:{field}"] = (params, field, True)
        for row in source["panel"]["rows"]:
            for field in ("name", *FIELDS):
                fields[f"{section}:panel:{int(row['id'])}:{field}"] = (row, field, field != "name")
    for row in doc["scenarios"]["rows"]:
        for field in row:
            if field not in ("id", "frequency_method", "cost_dist_type"):
                fields[f"scenario:{row_key(row['id'])}:{field}"] = (row, field, field != "name")
    return fields


def active_fields(doc):
    fields = {"seed"}
    if doc["workflow"]["frequency_mode"] == "scenario":
        for row in doc["scenarios"]["rows"]:
            prefix = f"scenario:{row_key(row['id'])}:"
            fields.add(prefix + "name")
            for section, method in (
                ("frequency", row["frequency_method"]),
                ("cost", row["cost_dist_type"]),
            ):
                fields.update(prefix + section + "_" + field for field in parameter_fields(method))
    else:
        for section in ("frequency", "cost"):
            distribution = doc[section]["distribution"]
            if doc["workflow"][section + "_mode"] == "direct":
                fields.update(
                    f"{section}:direct:{distribution}:{field}"
                    for field in parameter_fields(distribution)
                )
            else:
                for row in doc[section]["panel"]["rows"]:
                    fields.update(
                        f"{section}:panel:{int(row['id'])}:{field}"
                        for field in ("name", *parameter_fields(distribution))
                    )
    return fields


def validate_document(doc):
    """Validate the complete wire shape without discarding unfinished work."""
    require(isinstance(doc, dict) and doc.get("format") == FORMAT, "Not an annual-loss analysis")
    keys(
        doc,
        (
            "format",
            "version",
            "model_version",
            "id",
            "name",
            "created_at",
            "updated_at",
            "seed",
            "view",
            "workflow",
            "frequency",
            "cost",
            "scenarios",
            "drafts",
        ),
        "Analysis",
    )
    require(
        safe_integer(doc["version"]) and doc["version"] == VERSION,
        "Unsupported analysis format version; original preserved",
    )
    require(
        safe_integer(doc["model_version"]) and doc["model_version"] == MODEL_VERSION,
        "Unsupported model version; original preserved",
    )
    require(isinstance(doc["id"], str) and IDENTIFIER.fullmatch(doc["id"]), "Invalid analysis ID")
    require(isinstance(doc["name"], str) and doc["name"].strip(), "Analysis needs a name")
    for field in ("created_at", "updated_at"):
        require(isinstance(doc[field], str) and TIMESTAMP.fullmatch(doc[field]), f"Invalid {field}")
        try:
            datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"Invalid {field}") from error
    require(safe_integer(doc["seed"]), "Seed must be a non-negative safe integer")
    keys(doc["view"], ("chart", "focus_percentile", "confidence_level"), "View settings")
    require(doc["view"]["chart"] in ("pdf", "cdf"), "Unsupported chart view")
    require(
        number(doc["view"]["focus_percentile"]) and 95 <= doc["view"]["focus_percentile"] <= 99.9,
        "Outcome percentile must be between 95 and 99.9",
    )
    require(
        safe_integer(doc["view"]["confidence_level"], 50) and doc["view"]["confidence_level"] <= 95,
        "Central range must be between 50 and 95",
    )
    keys(
        doc["workflow"],
        ("frequency_mode", "cost_mode", "remembered_frequency_mode", "remembered_cost_mode"),
        "Workflow",
    )
    require(all(isinstance(v, str) for v in doc["workflow"].values()), "Invalid workflow mode")
    WorkflowModeState(**doc["workflow"])
    for section in ("frequency", "cost"):
        source = doc[section]
        keys(source, ("distribution", "direct", "panel"), section)
        require(source["distribution"] in DISTRIBUTIONS, "Unsupported distribution")
        keys(source["direct"], DISTRIBUTIONS, "Direct estimates")
        for distribution, params in source["direct"].items():
            keys(params, parameter_fields(distribution), "Direct parameters")
            require(all(number(v) for v in params.values()), "Invalid direct parameter type")
        panel = source["panel"]
        keys(panel, ("rows", "next_id"), "Panel")
        require(
            isinstance(panel["rows"], list) and len(panel["rows"]) >= 2,
            "Panel requires at least two experts",
        )
        ids = []
        for row in panel["rows"]:
            keys(row, ("id", "name", *FIELDS), "Panelist")
            require(safe_integer(row["id"], 1), "Invalid panelist ID")
            require(isinstance(row["name"], str), "Invalid panelist name")
            require(all(number(row[field]) for field in FIELDS), "Invalid panel parameter type")
            ids.append(row["id"])
        require(len(set(ids)) == len(ids), "Duplicate panelist IDs")
        require(
            safe_integer(panel["next_id"], 1) and panel["next_id"] > max(ids),
            "Invalid panel next_id",
        )
    scenarios = doc["scenarios"]
    keys(scenarios, ("rows", "next_id"), "Scenarios")
    require(
        isinstance(scenarios["rows"], list) and scenarios["rows"],
        "At least one scenario is required",
    )
    ids, integer_ids = [], []
    numeric_fields = (
        "frequency_odds",
        *(f"{s}_{f}" for s in ("frequency", "cost") for f in FIELDS),
    )
    for row in scenarios["rows"]:
        keys(row, ("id", "name", "frequency_method", "cost_dist_type", *numeric_fields), "Scenario")
        valid_id = safe_integer(row["id"], 1) or (
            isinstance(row["id"], str) and bool(IDENTIFIER.fullmatch(row["id"]))
        )
        require(valid_id, "Invalid scenario ID")
        ids.append(row_key(row["id"]))
        if not isinstance(row["id"], str):
            integer_ids.append(row["id"])
        require(isinstance(row["name"], str), "Invalid scenario name")
        require(row["frequency_method"] in (*DISTRIBUTIONS, "odds"), "Unsupported frequency method")
        require(row["cost_dist_type"] in DISTRIBUTIONS, "Unsupported cost distribution")
        require(
            all(number(row[field]) for field in numeric_fields), "Invalid scenario parameter type"
        )
    require(len(set(ids)) == len(ids), "Duplicate scenario IDs")
    require(
        safe_integer(scenarios["next_id"], 1)
        and scenarios["next_id"] > max(integer_ids, default=0),
        "Invalid scenario next_id",
    )
    require(isinstance(doc["drafts"], dict), "Invalid drafts")
    allowed = editable_fields(doc)
    require(
        all(path in allowed and isinstance(raw, str) for path, raw in doc["drafts"].items()),
        "Invalid draft field",
    )
    return doc


def make_document(name="Analysis 1"):
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    doc = {
        "format": FORMAT,
        "version": VERSION,
        "model_version": MODEL_VERSION,
        "id": str(uuid4()),
        "name": name,
        "created_at": now,
        "updated_at": now,
        "seed": 12345,
        "view": {"chart": "pdf", "focus_percentile": 99.5, "confidence_level": 90},
        "workflow": asdict(WorkflowModeState()),
        "drafts": {},
    }
    for section in ("frequency", "cost"):
        defaults = parameter_defaults(section)
        panel = PanelEditorState.from_rows(
            [{"id": i, "name": f"Panelist {i}", **defaults} for i in (1, 2)]
        )
        doc[section] = {
            "distribution": "lognormal",
            "direct": {
                dist: {key: defaults[key] for key in parameter_fields(dist)}
                for dist in DISTRIBUTIONS
            },
            "panel": {"rows": panel.to_rows(), "next_id": panel.next_id},
        }
    rows = []
    for scenario in DEFAULT_SCENARIOS:
        row = {
            "id": scenario.id,
            "name": scenario.name,
            "frequency_method": str(scenario.frequency_method),
            "cost_dist_type": str(scenario.cost_dist_type),
            "frequency_odds": 10.0,
        }
        for section, params in (
            ("frequency", scenario.frequency_params),
            ("cost", scenario.cost_params),
        ):
            values = {
                **parameter_defaults(section),
                **(asdict(params) if is_dataclass(params) else params),
            }
            row.update({f"{section}_{key}": value for key, value in values.items()})
        rows.append(row)
    scenarios = ScenarioEditorState.from_rows(rows)
    doc["scenarios"] = {"rows": scenarios.to_rows(), "next_id": scenarios.next_id}
    return validate_document(doc)


def serialize_backup(documents, *, library=False):
    docs = [validate_document(deepcopy(doc)) for doc in documents]
    require(bool(docs), "Library contains no analyses")
    require(len({doc["id"] for doc in docs}) == len(docs), "Duplicate analysis IDs")
    require(library or len(docs) == 1, "Choose one analysis to download")
    value = (
        {
            "format": LIBRARY_FORMAT,
            "version": VERSION,
            "analyses": sorted(docs, key=lambda doc: doc["id"]),
        }
        if library
        else docs[0]
    )
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def parse_backup(content):
    if isinstance(content, bytes):
        require(len(content) <= MAX_BACKUP_BYTES, "Backup exceeds 10 MiB")
        content = content.decode("utf-8")
    require(isinstance(content, str), "Backup must be UTF-8 JSON")
    require(len(content.encode("utf-8")) <= MAX_BACKUP_BYTES, "Backup exceeds 10 MiB")
    value = json.loads(content.removeprefix("\ufeff"))
    if isinstance(value, dict) and value.get("format") == LIBRARY_FORMAT:
        keys(value, ("format", "version", "analyses"), "Library")
        require(
            safe_integer(value["version"]) and value["version"] == VERSION,
            "Unsupported library version",
        )
        require(
            isinstance(value["analyses"], list) and value["analyses"],
            "Library contains no analyses",
        )
        docs = value["analyses"]
    else:
        docs = [value]
    for doc in docs:
        validate_document(doc)
    require(len({doc["id"] for doc in docs}) == len(docs), "Duplicate analysis IDs")
    return docs
