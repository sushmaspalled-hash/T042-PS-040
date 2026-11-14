from decimal import Decimal

from services.command_processor import calculate_loyalty_points


def test_points_without_discount():
    assert calculate_loyalty_points(500) == 50


def test_points_after_loyalty_redemption():
    # Original ticket price ₹500
    # Loyalty discount ₹100
    # Final ticket price ₹400
    assert calculate_loyalty_points(400) == 40


def test_points_exclude_gst_and_convenience_fee():
    # Ticket price ₹400; GST and fees are not included.
    assert calculate_loyalty_points(400) == 40


def test_points_below_ten_rupees():
    assert calculate_loyalty_points(9) == 0


def test_points_with_decimal_price():
    assert calculate_loyalty_points(259.50) == 25