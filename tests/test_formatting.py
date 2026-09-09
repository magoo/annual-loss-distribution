from __future__ import annotations

from decimal import Decimal

import pytest

from annual_loss.formatting import (
    EM_DASH,
    format_compact,
    format_incident_count,
    format_percentile,
    format_value,
)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "not-a-number", True])
def test_format_value_uses_em_dash_for_unavailable_values(value: object) -> None:
    assert format_value(value, use_dollars=True) == EM_DASH


def test_format_value_rounds_currency_and_groups_thousands() -> None:
    assert format_value(1234.2, use_dollars=True) == "$1,234"
    assert format_value(1234.8, use_dollars=True) == "$1,235"
    assert format_value(Decimal("2.5"), use_dollars=True) == "$3"


def test_format_value_keeps_at_most_two_non_currency_decimal_places() -> None:
    assert format_value(1234.567) == "1,234.57"
    assert format_value(1234) == "1,234"
    assert format_value(-0.001) == "0"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_500, "$1.5K"),
        (2_500_000, "$2.5M"),
        (3_200_000_000, "$3.2B"),
        (-1_500, "$-1.5K"),
    ],
)
def test_format_compact_uses_currency_suffixes(value: float, expected: str) -> None:
    assert format_compact(value, use_dollars=True) == expected


def test_format_compact_only_shortens_large_non_currency_values() -> None:
    assert format_compact(1_500) == "1,500"
    assert format_compact(2_500_000) == "2.5M"
    assert format_compact(-3_200_000_000) == "-3.2B"


def test_format_compact_falls_back_to_regular_formatting() -> None:
    assert format_compact(999, use_dollars=True) == "$999"
    assert format_compact(999.25) == "999.25"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.025, "P2.5"), (2.5, "P2.5"), (0.5, "P50"), (1, "P100"), (95, "P95")],
)
def test_format_percentile_accepts_probabilities_or_percentages(
    value: float,
    expected: str,
) -> None:
    assert format_percentile(value) == expected


@pytest.mark.parametrize("value", [-0.1, 101, None, float("nan")])
def test_format_percentile_rejects_invalid_values(value: object) -> None:
    assert format_percentile(value) == EM_DASH


def test_format_incident_count_is_whole_and_non_negative() -> None:
    assert format_incident_count(12.5) == "13"
    assert format_incident_count(-2) == "0"
    assert format_incident_count(None) == EM_DASH
