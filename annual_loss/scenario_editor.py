"""Pure immutable state for the notebook's dynamic scenario editor.

This module intentionally has no Marimo dependency. UI cells can render every
row, synchronize their current widget values with :meth:`with_rows`, and then
apply structural add/remove transitions as ordinary immutable operations.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from numbers import Integral
from typing import Any, TypeAlias

from .models import DistributionType, FrequencyMethod

ScenarioId: TypeAlias = int | str

FREQUENCY_METHODS = tuple(method.value for method in FrequencyMethod)
COST_DISTRIBUTIONS = tuple(distribution.value for distribution in DistributionType)

FREQUENCY_PARAMETER_FIELDS: dict[str, tuple[str, ...]] = {
    FrequencyMethod.ODDS.value: ("odds",),
    FrequencyMethod.LOGNORMAL.value: ("p50", "p95"),
    FrequencyMethod.PERT.value: ("min", "mode", "max"),
    FrequencyMethod.PARETO.value: ("p50", "p95"),
}
COST_PARAMETER_FIELDS: dict[str, tuple[str, ...]] = {
    DistributionType.LOGNORMAL.value: ("p50", "p95"),
    DistributionType.PERT.value: ("min", "mode", "max"),
    DistributionType.PARETO.value: ("p50", "p95"),
}

_DEFAULT_ROW_VALUES: dict[str, Any] = {
    "frequency_method": FrequencyMethod.ODDS.value,
    "frequency_odds": 10.0,
    "frequency_p50": 1.0,
    "frequency_p95": 10.0,
    "frequency_min": 0.0,
    "frequency_mode": 1.0,
    "frequency_max": 10.0,
    "cost_dist_type": DistributionType.LOGNORMAL.value,
    "cost_p50": 50_000.0,
    "cost_p95": 500_000.0,
    "cost_min": 1_000.0,
    "cost_mode": 50_000.0,
    "cost_max": 500_000.0,
}


@dataclass(frozen=True, slots=True)
class ScenarioEditorRow:
    """One flat editor row, including values hidden by the current methods."""

    id: ScenarioId
    name: str
    frequency_method: str
    frequency_odds: Any
    frequency_p50: Any
    frequency_p95: Any
    frequency_min: Any
    frequency_mode: Any
    frequency_max: Any
    cost_dist_type: str
    cost_p50: Any
    cost_p95: Any
    cost_min: Any
    cost_mode: Any
    cost_max: Any

    def __post_init__(self) -> None:
        _validate_id(self.id)
        if not isinstance(self.name, str):
            raise TypeError("scenario name must be a string")
        _normalize_frequency_method(self.frequency_method)
        _normalize_cost_distribution(self.cost_dist_type)

    @classmethod
    def from_flat_row(
        cls,
        row: Mapping[str, Any],
        *,
        assigned_id: ScenarioId | None = None,
    ) -> ScenarioEditorRow:
        """Normalize a flat row and fill every hidden parameter slot."""

        if not isinstance(row, Mapping):
            raise TypeError("scenario rows must be mappings")
        scenario_id = row.get("id") if assigned_id is None else assigned_id
        if scenario_id is None:
            raise ValueError("scenario row is missing an id")
        values = {**_DEFAULT_ROW_VALUES, **row}
        return cls(
            id=scenario_id,
            name=str(values.get("name", f"Scenario {scenario_id}")),
            frequency_method=_normalize_frequency_method(values["frequency_method"]),
            frequency_odds=values["frequency_odds"],
            frequency_p50=values["frequency_p50"],
            frequency_p95=values["frequency_p95"],
            frequency_min=values["frequency_min"],
            frequency_mode=values["frequency_mode"],
            frequency_max=values["frequency_max"],
            cost_dist_type=_normalize_cost_distribution(values["cost_dist_type"]),
            cost_p50=values["cost_p50"],
            cost_p95=values["cost_p95"],
            cost_min=values["cost_min"],
            cost_mode=values["cost_mode"],
            cost_max=values["cost_max"],
        )

    def to_flat_row(self) -> dict[str, Any]:
        """Return a fresh Marimo-table-compatible mapping."""

        return {
            "id": self.id,
            "name": self.name,
            "frequency_method": self.frequency_method,
            "frequency_odds": self.frequency_odds,
            "frequency_p50": self.frequency_p50,
            "frequency_p95": self.frequency_p95,
            "frequency_min": self.frequency_min,
            "frequency_mode": self.frequency_mode,
            "frequency_max": self.frequency_max,
            "cost_dist_type": self.cost_dist_type,
            "cost_p50": self.cost_p50,
            "cost_p95": self.cost_p95,
            "cost_min": self.cost_min,
            "cost_mode": self.cost_mode,
            "cost_max": self.cost_max,
        }


@dataclass(frozen=True, slots=True)
class ScenarioEditorState:
    """An immutable, non-empty ordered collection of stable scenario rows."""

    rows: tuple[ScenarioEditorRow, ...]
    next_id: int | None = None

    def __post_init__(self) -> None:
        rows = tuple(self.rows)
        object.__setattr__(self, "rows", rows)
        if not rows:
            raise ValueError("scenario editor requires at least one row")
        if any(not isinstance(row, ScenarioEditorRow) for row in rows):
            raise TypeError("rows must contain ScenarioEditorRow objects")
        ids = [row.id for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("scenario row ids must be unique")
        minimum_next_id = _next_unique_integer_id(set(ids))
        next_id = minimum_next_id if self.next_id is None else self.next_id
        if isinstance(next_id, bool) or not isinstance(next_id, Integral) or next_id < 1:
            raise ValueError("next_id must be a positive integer")
        if next_id in ids:
            raise ValueError("next_id must not identify an existing scenario row")
        if next_id < minimum_next_id:
            raise ValueError("next_id must be greater than existing integer ids")
        object.__setattr__(self, "next_id", int(next_id))

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, Any] | ScenarioEditorRow],
    ) -> ScenarioEditorState:
        """Initialize state from flat mappings, assigning any missing IDs safely."""

        if isinstance(rows, (str, bytes, Mapping)):
            raise TypeError("rows must be an iterable of flat scenario rows")
        source_rows = list(rows)
        if not source_rows:
            raise ValueError("scenario editor requires at least one row")

        supplied_ids: list[ScenarioId] = []
        for row in source_rows:
            if isinstance(row, ScenarioEditorRow):
                scenario_id = row.id
            elif isinstance(row, Mapping):
                scenario_id = row.get("id")
            else:
                raise TypeError("scenario rows must be mappings or ScenarioEditorRow objects")
            if scenario_id is not None:
                _validate_id(scenario_id)
                supplied_ids.append(scenario_id)
        if len(set(supplied_ids)) != len(supplied_ids):
            raise ValueError("scenario row ids must be unique")

        used_ids = set(supplied_ids)
        normalized: list[ScenarioEditorRow] = []
        for row in source_rows:
            if isinstance(row, ScenarioEditorRow):
                normalized.append(row)
                continue
            scenario_id = row.get("id")
            if scenario_id is None:
                scenario_id = _next_unique_integer_id(used_ids)
                used_ids.add(scenario_id)
            normalized.append(ScenarioEditorRow.from_flat_row(row, assigned_id=scenario_id))

        return cls(rows=tuple(normalized))

    def to_rows(self) -> list[dict[str, Any]]:
        """Return fresh flat mappings in display order."""

        return [row.to_flat_row() for row in self.rows]

    def with_rows(
        self,
        rows: Iterable[Mapping[str, Any] | ScenarioEditorRow],
    ) -> ScenarioEditorState:
        """Synchronize widget values without allowing structural row changes.

        Incoming rows must carry exactly the same stable IDs in exactly the
        same order. Missing fields are merged from the corresponding existing
        row, which preserves parameter values hidden by the selected methods.
        """

        if isinstance(rows, (str, bytes, Mapping)):
            raise TypeError("rows must be an iterable of flat scenario rows")
        source_rows = list(rows)
        incoming_ids: list[ScenarioId] = []
        for row in source_rows:
            if isinstance(row, ScenarioEditorRow):
                scenario_id = row.id
            elif isinstance(row, Mapping):
                scenario_id = row.get("id")
                if scenario_id is None:
                    raise ValueError("synchronized scenario rows must include stable ids")
            else:
                raise TypeError("scenario rows must be mappings or ScenarioEditorRow objects")
            _validate_id(scenario_id)
            incoming_ids.append(scenario_id)

        expected_ids = [row.id for row in self.rows]
        if incoming_ids != expected_ids:
            raise ValueError(
                "synchronized scenario rows must preserve the same stable ids in the same order"
            )

        normalized: list[ScenarioEditorRow] = []
        for current, incoming in zip(self.rows, source_rows, strict=True):
            if isinstance(incoming, ScenarioEditorRow):
                normalized.append(incoming)
            else:
                merged = current.to_flat_row()
                merged.update(incoming)
                normalized.append(ScenarioEditorRow.from_flat_row(merged, assigned_id=current.id))
        normalized_rows = tuple(normalized)
        if normalized_rows == self.rows:
            return self
        return ScenarioEditorState(rows=normalized_rows, next_id=self.next_id)

    def add_scenario(self) -> ScenarioEditorState:
        """Append a complete safe-default scenario."""

        assert self.next_id is not None
        scenario_id = self.next_id
        new_row = ScenarioEditorRow.from_flat_row(
            {
                "id": scenario_id,
                "name": f"New scenario {scenario_id}",
            }
        )
        return ScenarioEditorState(
            rows=self.rows + (new_row,),
            next_id=_next_unique_integer_id({row.id for row in self.rows} | {scenario_id}),
        )

    def remove_scenario(self, scenario_id: ScenarioId) -> ScenarioEditorState:
        """Remove one stable ID, while keeping the final required row."""

        matching_indexes = [index for index, row in enumerate(self.rows) if row.id == scenario_id]
        if not matching_indexes:
            raise KeyError(f"unknown scenario id: {scenario_id!r}")
        if len(self.rows) == 1:
            return self
        removed_index = matching_indexes[0]
        remaining = self.rows[:removed_index] + self.rows[removed_index + 1 :]
        return ScenarioEditorState(rows=remaining, next_id=self.next_id)


def frequency_parameter_fields(method: FrequencyMethod | str) -> tuple[str, ...]:
    """Return the unprefixed parameter names visible for a frequency method."""

    return FREQUENCY_PARAMETER_FIELDS[_normalize_frequency_method(method)]


def cost_parameter_fields(distribution: DistributionType | str) -> tuple[str, ...]:
    """Return the unprefixed parameter names visible for a cost distribution."""

    return COST_PARAMETER_FIELDS[_normalize_cost_distribution(distribution)]


def _normalize_frequency_method(value: FrequencyMethod | DistributionType | str) -> str:
    raw_value = getattr(value, "value", value)
    try:
        return FrequencyMethod(raw_value).value
    except (TypeError, ValueError) as exc:
        choices = ", ".join(FREQUENCY_METHODS)
        raise ValueError(f"unsupported frequency method {value!r}; choose {choices}") from exc


def _normalize_cost_distribution(value: DistributionType | FrequencyMethod | str) -> str:
    raw_value = getattr(value, "value", value)
    try:
        return DistributionType(raw_value).value
    except (TypeError, ValueError) as exc:
        choices = ", ".join(COST_DISTRIBUTIONS)
        raise ValueError(f"unsupported cost distribution {value!r}; choose {choices}") from exc


def _validate_id(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (Integral, str)):
        raise TypeError("scenario id must be an integer or string")
    if not isinstance(value, Hashable):
        raise TypeError("scenario id must be hashable")


def _next_unique_integer_id(existing_ids: set[ScenarioId]) -> int:
    integer_ids = [
        int(value)
        for value in existing_ids
        if isinstance(value, Integral) and not isinstance(value, bool)
    ]
    candidate = max((value for value in integer_ids if value >= 0), default=0) + 1
    while candidate in existing_ids:
        candidate += 1
    return candidate
