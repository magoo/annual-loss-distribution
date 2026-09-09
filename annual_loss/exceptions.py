"""Domain-specific exceptions for the annual-loss engine."""

from __future__ import annotations

from collections.abc import Mapping


class AnnualLossError(ValueError):
    """Base class for invalid models and unsafe simulations."""


class ParameterValidationError(AnnualLossError):
    """Raised when distribution parameters fail field-level validation."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors = dict(errors)
        details = "; ".join(f"{field}: {message}" for field, message in errors.items())
        super().__init__(details or "invalid distribution parameters")


class SimulationSafetyError(AnnualLossError):
    """Raised when a requested simulation exceeds a hard work limit."""
