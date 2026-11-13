from decimal import Decimal, ROUND_HALF_UP
from database.db import get_connection


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def calculate_points(ticket_total):
    """BR-09: Earn 1 point for every Rs.10 spent on tickets."""
    return int(money(ticket_total) // Decimal("10"))


def calculate_redemption(points_available, ticket_total, points_to_redeem):
    """
    100 points = Rs.50 discount.
    Maximum redemption is 50% of ticket price.
    """

    if points_to_redeem < 0:
        raise ValueError("Redemption points cannot be negative.")

    if points_to_redeem > points_available:
        raise ValueError("Insufficient loyalty points.")

    if points_to_redeem % 100 != 0:
        raise ValueError("Points must be redeemed in multiples of 100.")

    maximum_discount = money(money(ticket_total) * Decimal("0.50"))

    requested_discount = money(
        Decimal(points_to_redeem) / Decimal("100") * Decimal("50")
    )

    discount = min(requested_discount, maximum_discount)

    points_used = int(discount / Decimal("50") * Decimal("100"))

    return {
        "points_used": points_used,
        "discount": float(discount),
        "remaining_points": points_available - points_used
    }


def add_loyalty_points(customer_id, ticket_total):
    """Add earned points to a customer's account."""

    points = calculate_points(ticket_total)
    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            UPDATE customers
            SET loyalty_points = loyalty_points + ?
            WHERE customer_id = ?
            """,
            (points, customer_id)
        )

        if cursor.rowcount == 0:
            raise ValueError("Customer not found.")

        conn.commit()
        return points

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def redeem_loyalty_points(customer_id, ticket_total, points_to_redeem):
    """Redeem points and deduct them from the customer's balance."""

    conn = get_connection()

    try:
        customer = conn.execute(
            "SELECT loyalty_points FROM customers WHERE customer_id = ?",
            (customer_id,)
        ).fetchone()

        if customer is None:
            raise ValueError("Customer not found.")

        result = calculate_redemption(
            customer[0],
            ticket_total,
            points_to_redeem
        )

        conn.execute(
            """
            UPDATE customers
            SET loyalty_points = loyalty_points - ?
            WHERE customer_id = ?
            """,
            (result["points_used"], customer_id)
        )

        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def reverse_loyalty_points(customer_id, points):
    """Reverse earned points when a booking is cancelled."""

    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            UPDATE customers
            SET loyalty_points = MAX(0, loyalty_points - ?)
            WHERE customer_id = ?
            """,
            (points, customer_id)
        )

        if cursor.rowcount == 0:
            raise ValueError("Customer not found.")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()