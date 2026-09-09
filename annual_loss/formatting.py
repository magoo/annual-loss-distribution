"""Human-readable formatting for annual-loss model outputs.

The functions in this module deliberately avoid locale-dependent behavior so
reports and tests render consistently on every workstation and in CI.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

EM_DASH = "—"


def _as_decimal(value: Any) -> Decimal | None:
    """Return a finite decimal representation, or ``None`` for missing data."""

    if value is None or isinstance(value, bool):
        return None

    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    return number if number.is_finite() else None


def _format_decimal(value: Decimal, maximum_fraction_digits: int) -> str:
    quantum = Decimal(1).scaleb(-maximum_fraction_digits)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)

    rendered = f"{rounded:,.{maximum_fraction_digits}f}"
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def format_value(value: Any, use_dollars: bool = False) -> str:
    """Format a model value using the source application's display rules.

    Dollar amounts are rounded to whole dollars. Other values retain at most
    two decimal places. Missing and non-finite values use an em dash.

    Examples:
        >>> format_value(1234.8, use_dollars=True)
        '$1,235'
        >>> format_value(1234.567)
        '1,234.57'
    """

    number = _as_decimal(value)
    if number is None:
        return EM_DASH

    digits = 0 if use_dollars else 2
    rendered = _format_decimal(number, digits)
    return f"${rendered}" if use_dollars else rendered


def format_compact(value: Any, use_dollars: bool = False) -> str:
    """Format large values compactly, such as ``$2.4M``.

    Currency values use K, M, and B suffixes. Non-currency quantities only use
    M and B so ordinary incident counts remain easy to read (for example,
    ``1,500`` rather than ``1.5K``).
    """

    number = _as_decimal(value)
    if number is None:
        return EM_DASH

    absolute = abs(number)
    scale: Decimal | None = None
    suffix = ""

    if absolute >= Decimal("1e9"):
        scale, suffix = Decimal("1e9"), "B"
    elif absolute >= Decimal("1e6"):
        scale, suffix = Decimal("1e6"), "M"
    elif use_dollars and absolute >= Decimal("1e3"):
        scale, suffix = Decimal("1e3"), "K"

    if scale is None:
        return format_value(number, use_dollars=use_dollars)

    rendered = _format_decimal(number / scale, 1)
    prefix = "$" if use_dollars else ""
    return f"{prefix}{rendered}{suffix}"


def format_percentile(value: Any, maximum_fraction_digits: int = 1) -> str:
    """Format a percentile as a compact ``P`` label.

    Values in the inclusive range 0–1 are interpreted as probabilities;
    values above 1 are interpreted as percentages. Invalid values use an em
    dash. This permits both ``0.025`` and ``2.5`` to render as ``P2.5``.
    """

    number = _as_decimal(value)
    if number is None or number < 0 or number > 100:
        return EM_DASH
    if number <= 1:
        number *= 100

    return f"P{_format_decimal(number, maximum_fraction_digits)}"


def format_incident_count(value: Any) -> str:
    """Format a confidence bound as a non-negative whole incident count."""

    number = _as_decimal(value)
    if number is None:
        return EM_DASH
    return _format_decimal(max(number, Decimal(0)), 0)
