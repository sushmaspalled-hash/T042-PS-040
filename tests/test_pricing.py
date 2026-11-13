
import pytest
from decimal import Decimal

from services.pricing_service import (
    calculate_dynamic_multiplier,
    calculate_convenience_fee
)


# BR-03: Dynamic pricing tests

def test_occupancy_below_50_percent():
    assert calculate_dynamic_multiplier(49) == Decimal("1.00")


def test_occupancy_exactly_50_percent():
    assert calculate_dynamic_multiplier(50) == Decimal("1.15")


def test_occupancy_at_79_percent():
    assert calculate_dynamic_multiplier(79) == Decimal("1.15")


def test_occupancy_at_80_percent():
    assert calculate_dynamic_multiplier(80) == Decimal("1.30")


def test_occupancy_above_80_percent():
    assert calculate_dynamic_multiplier(90) == Decimal("1.30")


# BR-05: Convenience fee tests

def test_convenience_fee_for_two_tickets():
    result = calculate_convenience_fee(2)

    assert result["convenience_fee"] == 60.0
    assert result["convenience_gst"] == 10.8
    assert result["total_fee"] == 70.8


def test_convenience_fee_for_four_tickets():
    result = calculate_convenience_fee(4)

    assert result["convenience_fee"] == 110.0
    assert result["convenience_gst"] == 19.8
    assert result["total_fee"] == 129.8


def test_zero_tickets():
    with pytest.raises(ValueError):
        calculate_convenience_fee(0)