"""Pure immutable state for dynamic expert-panel editors.

Marimo cells can render the rows, synchronize their current widget values with
``with_rows``, and then apply structural add/remove transitions.  Every row keeps
all distribution fields so switching between P50/P95 and PERT inputs never loses
the values that are temporarily hidden by the UI.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from numbers import Integral
from typing import Any

_PARAMETER_FIELDS = ("p50", "p95", "min", "mode", "max")
_EMPTY_PARAMETER_VALUES = dict.fromkeys(_PARAMETER_FIELDS)


@dataclass(frozen=True, slots=True)
class PanelEditorRow:
    """One stable panelist row, including every potentially hidden field."""

    id: int
    name: str
    p50: Any
    p95: Any
    min: Any
    mode: Any
    max: Any

    def __post_init__(self) -> None:
        _validate_id(self.id)
        if not isinstance(self.name, str):
            raise TypeError("panelist name must be a string")

    @classmethod
    def from_flat_row(
        cls,
        row: Mapping[str, Any],
        *,
        assigned_id: int | None = None,
    ) -> PanelEditorRow:
        """Normalize a table row and fill parameter fields that are not visible."""

        if not isinstance(row, Mapping):
            raise TypeError("panel rows must be mappings")
        panelist_id = row.get("id") if assigned_id is None else assigned_id
        if panelist_id is None:
            raise ValueError("panel row is missing an id")
        values = {**_EMPTY_PARAMETER_VALUES, **row}
        name = values.get("name", f"Panelist {panelist_id}")
        if not isinstance(name, str):
            raise TypeError("panelist name must be a string")
        return cls(
            id=panelist_id,
            name=name,
            p50=values["p50"],
            p95=values["p95"],
            min=values["min"],
            mode=values["mode"],
            max=values["max"],
        )

    def to_flat_row(self) -> dict[str, Any]:
        """Return a fresh Marimo-table-compatible mapping."""

        return {
            "id": self.id,
            "name": self.name,
            "p50": self.p50,
            "p95": self.p95,
            "min": self.min,
            "mode": self.mode,
            "max": self.max,
        }


@dataclass(frozen=True, slots=True)
class PanelEditorState:
    """An immutable ordered panel with stable, monotonically allocated IDs."""

    rows: tuple[PanelEditorRow, ...]
    next_id: int | None = None

    def __post_init__(self) -> None:
        rows = tuple(self.rows)
        object.__setattr__(self, "rows", rows)
        if len(rows) < 2:
            raise ValueError("panel editor requires at least two panelists")
        if any(not isinstance(row, PanelEditorRow) for row in rows):
            raise TypeError("rows must contain PanelEditorRow objects")

        ids = [row.id for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("panel row ids must be unique")
        minimum_next_id = max(ids) + 1
        next_id = minimum_next_id if self.next_id is None else self.next_id
        if isinstance(next_id, bool) or not isinstance(next_id, Integral) or next_id < 1:
            raise ValueError("next_id must be a positive integer")
        if next_id < minimum_next_id:
            raise ValueError("next_id must be greater than every existing panel row id")
        object.__setattr__(self, "next_id", int(next_id))

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, Any] | PanelEditorRow],
    ) -> PanelEditorState:
        """Initialize a panel, assigning missing IDs above all supplied IDs."""

        source_rows = _materialize_rows(rows)
        if len(source_rows) < 2:
            raise ValueError("panel editor requires at least two panelists")

        supplied_ids: list[int] = []
        for row in source_rows:
            if isinstance(row, PanelEditorRow):
                panelist_id = row.id
            elif isinstance(row, Mapping):
                panelist_id = row.get("id")
            else:
                raise TypeError("panel rows must be mappings or PanelEditorRow objects")
            if panelist_id is not None:
                _validate_id(panelist_id)
                supplied_ids.append(panelist_id)
        if len(set(supplied_ids)) != len(supplied_ids):
            raise ValueError("panel row ids must be unique")

        next_id = max(supplied_ids, default=0) + 1
        normalized: list[PanelEditorRow] = []
        for row in source_rows:
            if isinstance(row, PanelEditorRow):
                normalized.append(row)
                continue
            panelist_id = row.get("id")
            if panelist_id is None:
                panelist_id = next_id
                next_id += 1
            normalized.append(PanelEditorRow.from_flat_row(row, assigned_id=panelist_id))
        return cls(rows=tuple(normalized), next_id=next_id)

    def with_rows(
        self,
        rows: Iterable[Mapping[str, Any] | PanelEditorRow],
    ) -> PanelEditorState:
        """Synchronize values while preserving row identity, order, and hidden fields."""

        source_rows = _materialize_rows(rows)
        incoming_ids: list[int] = []
        for row in source_rows:
            if isinstance(row, PanelEditorRow):
                panelist_id = row.id
            elif isinstance(row, Mapping):
                panelist_id = row.get("id")
                if panelist_id is None:
                    raise ValueError("synchronized panel rows must include stable ids")
            else:
                raise TypeError("panel rows must be mappings or PanelEditorRow objects")
            _validate_id(panelist_id)
            incoming_ids.append(panelist_id)

        expected_ids = [row.id for row in self.rows]
        if incoming_ids != expected_ids:
            raise ValueError(
                "synchronized panel rows must preserve the same stable ids in the same order"
            )

        normalized: list[PanelEditorRow] = []
        for current, incoming in zip(self.rows, source_rows, strict=True):
            if isinstance(incoming, PanelEditorRow):
                normalized.append(incoming)
            else:
                merged = current.to_flat_row()
                merged.update(incoming)
                normalized.append(PanelEditorRow.from_flat_row(merged, assigned_id=current.id))
        normalized_rows = tuple(normalized)
        if normalized_rows == self.rows:
            return self
        return PanelEditorState(rows=normalized_rows, next_id=self.next_id)

    def to_rows(self) -> list[dict[str, Any]]:
        """Return fresh flat mappings in display order."""

        return [row.to_flat_row() for row in self.rows]

    def add_panelist(
        self,
        defaults: Mapping[str, Any],
        *,
        name: str | None = None,
    ) -> PanelEditorState:
        """Append a named panelist initialized with all five parameter defaults."""

        if not isinstance(defaults, Mapping):
            raise TypeError("panelist defaults must be a mapping")
        missing = [field for field in _PARAMETER_FIELDS if field not in defaults]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(
                f"panelist defaults must include all parameter fields; missing: {fields}"
            )
        assert self.next_id is not None
        panelist_id = self.next_id
        resolved_name = defaults.get("name", f"Panelist {panelist_id}") if name is None else name
        if not isinstance(resolved_name, str):
            raise TypeError("panelist name must be a string")
        row = PanelEditorRow.from_flat_row(
            {**defaults, "id": panelist_id, "name": resolved_name},
            assigned_id=panelist_id,
        )
        return PanelEditorState(
            rows=self.rows + (row,),
            next_id=panelist_id + 1,
        )

    def remove_panelist(self, panelist_id: int) -> PanelEditorState:
        """Remove an ID without allowing the panel to fall below two members."""

        _validate_id(panelist_id)
        matching_indexes = [index for index, row in enumerate(self.rows) if row.id == panelist_id]
        if not matching_indexes:
            raise KeyError(f"unknown panelist id: {panelist_id!r}")
        if len(self.rows) == 2:
            return self
        removed_index = matching_indexes[0]
        remaining = self.rows[:removed_index] + self.rows[removed_index + 1 :]
        return PanelEditorState(rows=remaining, next_id=self.next_id)


def _materialize_rows(
    rows: Iterable[Mapping[str, Any] | PanelEditorRow],
) -> list[Mapping[str, Any] | PanelEditorRow]:
    if isinstance(rows, (str, bytes, Mapping)):
        raise TypeError("rows must be an iterable of flat panel rows")
    try:
        return list(rows)
    except TypeError as exc:
        raise TypeError("rows must be an iterable of flat panel rows") from exc


def _validate_id(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValueError("panel row ids must be positive integers")
