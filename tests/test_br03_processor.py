from decimal import Decimal
from services.command_processor import CommandProcessor


def test_dynamic_pricing_below_50_percent():
    processor = CommandProcessor.__new__(CommandProcessor)

    result = processor.calculate_dynamic_multiplier(
        Decimal("49.99")
    )

    assert result == Decimal("1.0")


def test_dynamic_pricing_at_50_percent():
    processor = CommandProcessor.__new__(CommandProcessor)

    result = processor.calculate_dynamic_multiplier(
        Decimal("50")
    )

    assert result == Decimal("1.15")


def test_dynamic_pricing_at_79_percent():
    processor = CommandProcessor.__new__(CommandProcessor)

    result = processor.calculate_dynamic_multiplier(
        Decimal("79")
    )

    assert result == Decimal("1.15")


def test_dynamic_pricing_at_80_percent():
    processor = CommandProcessor.__new__(CommandProcessor)

    result = processor.calculate_dynamic_multiplier(
        Decimal("80")
    )

    assert result == Decimal("1.30")


def test_dynamic_pricing_above_80_percent():
    processor = CommandProcessor.__new__(CommandProcessor)

    result = processor.calculate_dynamic_multiplier(
        Decimal("90")
    )

    assert result == Decimal("1.30")