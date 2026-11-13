from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from database.db import get_connection


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def parse_datetime(value):
    """Convert database datetime text into timezone-aware datetime."""

    result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


# --------------------------------------------------
# BR-10: REFUND CALCULATION
# --------------------------------------------------

def calculate_refund(ticket_total, hours_before_show):
    """
    More than 4 hours: 75% refund.
    2 to 4 hours: 50% refund.
    Less than 2 hours: 0% refund.

    Convenience fees are non-refundable.
    """

    ticket_total = money(ticket_total)

    if hours_before_show > 4:
        percentage = Decimal("0.75")

    elif hours_before_show >= 2:
        percentage = Decimal("0.50")

    else:
        percentage = Decimal("0.00")

    refund = money(ticket_total * percentage)

    return {
        "refund_percentage": float(percentage * 100),
        "refund_amount": float(refund)
    }


# --------------------------------------------------
# CUSTOMER BOOKING CANCELLATION
# --------------------------------------------------

def cancel_booking(booking_id):
    """Cancel a confirmed booking and calculate refund."""

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute(
            """
            SELECT
                b.customer_id,
                b.show_id,
                b.status,
                s.start_time
            FROM bookings b
            JOIN shows s ON b.show_id = s.show_id
            WHERE b.booking_id = ?
            """,
            (booking_id,)
        ).fetchone()

        if booking is None:
            raise ValueError("Booking not found.")

        customer_id, show_id, status, start_time = booking

        if status != "CONFIRMED":
            raise ValueError("Booking is not available for cancellation.")

        show_datetime = parse_datetime(start_time)
        now = datetime.now(timezone.utc)

        hours_before_show = (
            show_datetime - now
        ).total_seconds() / 3600

        tickets = conn.execute(
            """
            SELECT ticket_price
            FROM booking_seats
            WHERE booking_id = ?
            """,
            (booking_id,)
        ).fetchall()

        if not tickets:
            raise ValueError("No tickets found for this booking.")

        ticket_total = sum(
            (Decimal(str(ticket[0])) for ticket in tickets),
            Decimal("0.00")
        )

        refund_details = calculate_refund(
            ticket_total,
            hours_before_show
        )

        earned_points = int(ticket_total // Decimal("10"))

        # Cancel booking.
        conn.execute(
            """
            UPDATE bookings
            SET status = 'CANCELLED'
            WHERE booking_id = ?
            """,
            (booking_id,)
        )

        # Release booked seats.
        conn.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE customer_id = ?
              AND show_id = ?
              AND status = 'BOOKED'
              AND seat_id IN (
                  SELECT seat_id
                  FROM booking_seats
                  WHERE booking_id = ?
              )
            """,
            (customer_id, show_id, booking_id)
        )

        # Reverse loyalty points earned.
        conn.execute(
            """
            UPDATE customers
            SET loyalty_points =
                MAX(0, loyalty_points - ?)
            WHERE customer_id = ?
            """,
            (earned_points, customer_id)
        )

        conn.commit()

        return {
            "booking_id": booking_id,
            "customer_id": customer_id,
            "show_id": show_id,
            "status": "CANCELLED",
            "hours_before_show": round(hours_before_show, 2),
            "ticket_total": float(ticket_total),
            "refund_percentage": refund_details["refund_percentage"],
            "refund_amount": refund_details["refund_amount"],
            "loyalty_points_reversed": earned_points
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# --------------------------------------------------
# VENUE-INITIATED SHOW CANCELLATION
# --------------------------------------------------

def cancel_show_by_venue(show_id):
    """
    BR-10:

    Venue cancellation:
    1. Refund 100% including convenience fees and GST.
    2. Reverse original earned loyalty points.
    3. Award 2x loyalty points as compensation.
    4. Cancel all confirmed bookings.
    5. Release all seats and active holds.
    6. Mark the show as cancelled.
    """

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        show = conn.execute(
            """
            SELECT status
            FROM shows
            WHERE show_id = ?
            """,
            (show_id,)
        ).fetchone()

        if show is None:
            raise ValueError("Show not found.")

        if show[0] == "CANCELLED":
            raise ValueError("Show is already cancelled.")

        bookings = conn.execute(
            """
            SELECT booking_id, customer_id, total_amount
            FROM bookings
            WHERE show_id = ?
              AND status = 'CONFIRMED'
            """,
            (show_id,)
        ).fetchall()

        refund_results = []

        for booking_id, customer_id, total_amount in bookings:

            tickets = conn.execute(
                """
                SELECT ticket_price
                FROM booking_seats
                WHERE booking_id = ?
                """,
                (booking_id,)
            ).fetchall()

            ticket_total = sum(
                (Decimal(str(ticket[0])) for ticket in tickets),
                Decimal("0.00")
            )

            earned_points = int(
                ticket_total // Decimal("10")
            )

            compensation_points = earned_points * 2

            # Reverse original points and credit 2x compensation.
            conn.execute(
                """
                UPDATE customers
                SET loyalty_points =
                    MAX(0, loyalty_points - ?)
                    + ?
                WHERE customer_id = ?
                """,
                (
                    earned_points,
                    compensation_points,
                    customer_id
                )
            )

            # Cancel booking.
            conn.execute(
                """
                UPDATE bookings
                SET status = 'CANCELLED'
                WHERE booking_id = ?
                """,
                (booking_id,)
            )

            # Record full refund including fees and GST.
            refund_results.append({
                "booking_id": booking_id,
                "customer_id": customer_id,
                "refund_amount": float(money(total_amount)),
                "loyalty_compensation_points": compensation_points,
                "status": "CANCELLED"
            })

        # Release active and booked seats.
        conn.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE show_id = ?
              AND status IN ('ACTIVE', 'BOOKED')
            """,
            (show_id,)
        )

        # Cancel the show.
        conn.execute(
            """
            UPDATE shows
            SET status = 'CANCELLED'
            WHERE show_id = ?
            """,
            (show_id,)
        )

        conn.commit()

        return {
            "show_id": show_id,
            "show_status": "CANCELLED",
            "total_cancelled_bookings": len(refund_results),
            "refunds": refund_results
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()