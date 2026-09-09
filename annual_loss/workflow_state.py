"""Pure mode-transition state for linked scenario workflow controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .models import Section

InputMode: TypeAlias = Literal["direct", "panel", "scenario"]
NonScenarioMode: TypeAlias = Literal["direct", "panel"]
WorkflowSection: TypeAlias = Literal["frequency", "cost"]

_MODES = ("direct", "panel", "scenario")
_NON_SCENARIO_MODES = ("direct", "panel")
_SECTIONS = ("frequency", "cost")


@dataclass(frozen=True, slots=True)
class WorkflowModeState:
    """Effective input modes plus each section's remembered independent mode.

    Scenario selection is linked: the effective modes are either both Scenario or
    neither.  The remembered values make leaving Scenario restore the other side
    exactly as the user last configured it.
    """

    frequency_mode: InputMode = "direct"
    cost_mode: InputMode = "direct"
    remembered_frequency_mode: NonScenarioMode | None = None
    remembered_cost_mode: NonScenarioMode | None = None

    def __post_init__(self) -> None:
        frequency_mode = _normalize_mode(self.frequency_mode)
        cost_mode = _normalize_mode(self.cost_mode)
        frequency_is_scenario = frequency_mode == "scenario"
        cost_is_scenario = cost_mode == "scenario"
        if frequency_is_scenario != cost_is_scenario:
            raise ValueError("frequency and cost must enter or leave scenario mode together")

        remembered_frequency = self.remembered_frequency_mode
        remembered_cost = self.remembered_cost_mode
        if remembered_frequency is None:
            remembered_frequency = "direct" if frequency_is_scenario else frequency_mode
        if remembered_cost is None:
            remembered_cost = "direct" if cost_is_scenario else cost_mode
        remembered_frequency = _normalize_non_scenario_mode(
            remembered_frequency, "remembered_frequency_mode"
        )
        remembered_cost = _normalize_non_scenario_mode(remembered_cost, "remembered_cost_mode")

        if not frequency_is_scenario and remembered_frequency != frequency_mode:
            raise ValueError("remembered_frequency_mode must match the effective frequency mode")
        if not cost_is_scenario and remembered_cost != cost_mode:
            raise ValueError("remembered_cost_mode must match the effective cost mode")

        object.__setattr__(self, "frequency_mode", frequency_mode)
        object.__setattr__(self, "cost_mode", cost_mode)
        object.__setattr__(self, "remembered_frequency_mode", remembered_frequency)
        object.__setattr__(self, "remembered_cost_mode", remembered_cost)

    @property
    def scenario_mode(self) -> bool:
        """Whether the linked Scenario workflow is active."""

        return self.frequency_mode == self.cost_mode == "scenario"

    @property
    def frequency_non_scenario_mode(self) -> NonScenarioMode:
        """Alias describing the remembered Frequency mode."""

        assert self.remembered_frequency_mode is not None
        return self.remembered_frequency_mode

    @property
    def cost_non_scenario_mode(self) -> NonScenarioMode:
        """Alias describing the remembered Cost mode."""

        assert self.remembered_cost_mode is not None
        return self.remembered_cost_mode

    def select(
        self, section: WorkflowSection | Section | str, mode: InputMode | str
    ) -> WorkflowModeState:
        """Apply one Frequency/Cost mode selection as an immutable transition."""

        selected_section = _normalize_section(section)
        selected_mode = _normalize_mode(mode)

        if selected_mode == "scenario":
            if self.scenario_mode:
                return self
            return WorkflowModeState(
                frequency_mode="scenario",
                cost_mode="scenario",
                remembered_frequency_mode=self.frequency_non_scenario_mode,
                remembered_cost_mode=self.cost_non_scenario_mode,
            )

        if self.scenario_mode:
            if selected_section == "frequency":
                return WorkflowModeState(
                    frequency_mode=selected_mode,
                    cost_mode=self.cost_non_scenario_mode,
                    remembered_frequency_mode=selected_mode,
                    remembered_cost_mode=self.cost_non_scenario_mode,
                )
            return WorkflowModeState(
                frequency_mode=self.frequency_non_scenario_mode,
                cost_mode=selected_mode,
                remembered_frequency_mode=self.frequency_non_scenario_mode,
                remembered_cost_mode=selected_mode,
            )

        if selected_section == "frequency":
            if selected_mode == self.frequency_mode:
                return self
            return WorkflowModeState(
                frequency_mode=selected_mode,
                cost_mode=self.cost_mode,
                remembered_frequency_mode=selected_mode,
                remembered_cost_mode=self.cost_non_scenario_mode,
            )
        if selected_mode == self.cost_mode:
            return self
        return WorkflowModeState(
            frequency_mode=self.frequency_mode,
            cost_mode=selected_mode,
            remembered_frequency_mode=self.frequency_non_scenario_mode,
            remembered_cost_mode=selected_mode,
        )


def _normalize_section(value: WorkflowSection | Section | str) -> WorkflowSection:
    if not isinstance(value, str):
        raise TypeError("section must be 'frequency' or 'cost'")
    if value not in _SECTIONS:
        raise ValueError("section must be 'frequency' or 'cost'")
    return value  # type: ignore[return-value]


def _normalize_mode(value: InputMode | str) -> InputMode:
    if not isinstance(value, str):
        raise TypeError("mode must be 'direct', 'panel', or 'scenario'")
    if value not in _MODES:
        raise ValueError("mode must be 'direct', 'panel', or 'scenario'")
    return value  # type: ignore[return-value]


def _normalize_non_scenario_mode(value: object, field: str) -> NonScenarioMode:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be 'direct' or 'panel'")
    if value not in _NON_SCENARIO_MODES:
        raise ValueError(f"{field} must be 'direct' or 'panel'")
    return value  # type: ignore[return-value]
