from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    """Round amount to two decimal places."""
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def calculate_dynamic_multiplier(occupancy):
    """
    BR-03:
    Below 50%       = 1.00
    50% to 79.99%   = 1.15
    80% and above   = 1.30
    """

    if occupancy < 50:
        return Decimal("1.00")
    elif occupancy < 80:
        return Decimal("1.15")
    else:
        return Decimal("1.30")


def calculate_ticket_price(
    base_price,
    tier,
    occupancy,
    show_start,
    is_opening_day=False,
    seat_count=1,
    now=None
):
    """
    Calculate one ticket's price.

    Applies:
    BR-03 Dynamic pricing
    BR-04 Opening-day and last-minute pricing
    BR-06 Entertainment GST
    BR-07 Group discount
    BR-08 Weekday matinee discount
    """

    if now is None:
        now = datetime.now()

    show_start = datetime.fromisoformat(show_start) if isinstance(
        show_start, str
    ) else show_start

    price = money(base_price)

    # Step 1: Dynamic pricing
    multiplier = calculate_dynamic_multiplier(occupancy)
    price = money(price * multiplier)

    dynamic_price = price

    # Step 2: Time-based offers
    time_remaining = show_start - now

    if is_opening_day:
        # Opening-day offer wins over last-minute offer.
        price = money(price * Decimal("1.20"))

    elif (
        time_remaining <= timedelta(hours=2)
        and time_remaining >= timedelta(0)
        and tier.upper() == "CLASSIC"
    ):
        price = money(price * Decimal("0.90"))

    # Step 3: Group and matinee discounts
    group_discount = Decimal("0")
    matinee_discount = Decimal("0")

    if seat_count >= 6:
        group_discount = money(price * Decimal("0.10"))

    weekday_matinee = (
        show_start.weekday() < 5
        and show_start.hour < 12
        and tier.upper() in ("CLASSIC", "PRIME")
    )

    if weekday_matinee:
        matinee_discount = Decimal("50.00")

    # BR-07: Group and matinee do not stack.
    # Apply whichever discount is higher.
    discount = max(group_discount, matinee_discount)

    price = max(Decimal("0.00"), money(price - discount))

    # Step 4: Entertainment GST
    gst_rate = (
        Decimal("0.12")
        if price <= Decimal("100")
        else Decimal("0.18")
    )

    gst = money(price * gst_rate)

    final_ticket_price = money(price + gst)

    return {
        "base_price": float(money(base_price)),
        "occupancy": occupancy,
        "dynamic_multiplier": float(multiplier),
        "price_after_dynamic": float(dynamic_price),
        "ticket_discount": float(discount),
        "taxable_ticket_price": float(price),
        "gst_rate": float(gst_rate),
        "gst_amount": float(gst),
        "final_ticket_price": float(final_ticket_price)
    }


def calculate_convenience_fee(ticket_count):
    """
    BR-05:
    First 2 tickets: Rs.30 each
    Remaining tickets: Rs.25 each
    GST on convenience fee: 18%
    """

    if ticket_count <= 0:
        raise ValueError("Ticket count must be positive.")

    first_two = min(ticket_count, 2)
    remaining = max(0, ticket_count - 2)

    fee = (
        Decimal(first_two) * Decimal("30")
        + Decimal(remaining) * Decimal("25")
    )

    fee_gst = money(fee * Decimal("0.18"))

    return {
        "ticket_count": ticket_count,
        "convenience_fee": float(money(fee)),
        "convenience_gst": float(fee_gst),
        "total_fee": float(money(fee + fee_gst))
    }


def calculate_booking_price(
    ticket_prices,
    ticket_count
):
    """Calculate total booking amount."""

    ticket_total = money(
        sum(
            (Decimal(str(price)) for price in ticket_prices),
            Decimal("0")
        )
    )

    fees = calculate_convenience_fee(ticket_count)

    total = money(
        ticket_total + Decimal(str(fees["total_fee"]))
    )

    return {
        "ticket_total": float(ticket_total),
        "convenience_fee": fees["convenience_fee"],
        "convenience_gst": fees["convenience_gst"],
        "total_amount": float(total)
    }