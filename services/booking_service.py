from datetime import datetime, timezone
from decimal import Decimal

from database.db import get_connection

from services.pricing_service import (
    calculate_ticket_price,
    calculate_convenience_fee
)


def confirm_booking(customer_id, show_id, seat_ids):
    """
    Confirm a booking using active seat holds.

    BR-01: Only valid, unexpired holds can be booked.
    BR-03: Uses frozen occupancy from the seat hold.
    BR-05: Calculates convenience fee and GST.
    BR-06: Calculates entertainment GST through pricing service.
    BR-09: Awards loyalty points on ticket price excluding fees and GST.
    """

    if not seat_ids:
        raise ValueError("Please select at least one seat.")

    if len(seat_ids) > 10:
        raise ValueError("Maximum 10 seats can be booked.")

    if len(seat_ids) != len(set(seat_ids)):
        raise ValueError("Duplicate seats are not allowed.")

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        now = datetime.now(timezone.utc)
        now_text = now.isoformat()

        # 1. Validate customer
        customer = connection.execute(
            """
            SELECT customer_id
            FROM customers
            WHERE customer_id = ?
            """,
            (customer_id,)
        ).fetchone()

        if customer is None:
            raise ValueError("Customer not found.")

        # 2. Validate show
        show = connection.execute(
            """
            SELECT
                screen_id,
                start_time,
                is_opening_day,
                is_a_rated,
                status
            FROM shows
            WHERE show_id = ?
            """,
            (show_id,)
        ).fetchone()

        if show is None:
            raise ValueError("Show not found.")

        if show[4] not in ("ACTIVE", "SCHEDULED"):
            raise ValueError("Show is not available for booking.")

        screen_id = show[0]
        show_start = show[1]
        is_opening_day = bool(show[2])

        # 3. Release expired holds for this show
        connection.execute(
            """
            UPDATE seat_holds
            SET status = 'EXPIRED'
            WHERE show_id = ?
              AND status = 'ACTIVE'
              AND expires_at <= ?
            """,
            (show_id, now_text)
        )

        # 4. Validate active holds
        placeholders = ",".join("?" for _ in seat_ids)

        holds = connection.execute(
            f"""
            SELECT seat_id, frozen_occupancy
            FROM seat_holds
            WHERE customer_id = ?
              AND show_id = ?
              AND seat_id IN ({placeholders})
              AND status = 'ACTIVE'
              AND expires_at > ?
            """,
            (customer_id, show_id, *seat_ids, now_text)
        ).fetchall()

        if len(holds) != len(seat_ids):
            raise ValueError(
                "Some seats are not held by this customer "
                "or their holds have expired."
            )

        occupancy_by_seat = {
            hold[0]: hold[1] for hold in holds
        }

        # 5. Validate seats belong to this show's screen
        seats = connection.execute(
            f"""
            SELECT seat_id, tier
            FROM seats
            WHERE screen_id = ?
              AND seat_id IN ({placeholders})
            """,
            (screen_id, *seat_ids)
        ).fetchall()

        if len(seats) != len(seat_ids):
            raise ValueError(
                "One or more selected seats do not belong to this show."
            )

        seat_tiers = {
            seat[0]: seat[1] for seat in seats
        }

        # 6. Calculate ticket prices
        ticket_details = []

        for seat_id in seat_ids:

            tier = seat_tiers[seat_id]

            base_price_column = f"base_{tier.lower()}"

            base_price = connection.execute(
                f"""
                SELECT {base_price_column}
                FROM shows
                WHERE show_id = ?
                """,
                (show_id,)
            ).fetchone()[0]

            price = calculate_ticket_price(
                base_price=base_price,
                tier=tier,
                occupancy=occupancy_by_seat[seat_id],
                show_start=show_start,
                is_opening_day=is_opening_day,
                seat_count=len(seat_ids),
                now=datetime.now()
            )

            ticket_details.append({
                "seat_id": seat_id,
                "tier": tier,
                "ticket_price": price["taxable_ticket_price"],
                "gst_amount": price["gst_amount"]
            })

        # 7. Calculate convenience fee
        fees = calculate_convenience_fee(len(seat_ids))

        fee_per_ticket = (
            Decimal(str(fees["convenience_fee"]))
            / Decimal(len(seat_ids))
        )

        # 8. Calculate total ticket amount
        ticket_total = sum(
            Decimal(str(item["ticket_price"]))
            + Decimal(str(item["gst_amount"]))
            for item in ticket_details
        )

        total_amount = (
            ticket_total
            + Decimal(str(fees["total_fee"]))
        )

        # 9. Create booking record
        cursor = connection.execute(
            """
            INSERT INTO bookings (
                customer_id,
                show_id,
                booking_time,
                total_amount,
                status
            )
            VALUES (?, ?, ?, ?, 'CONFIRMED')
            """,
            (
                customer_id,
                show_id,
                now_text,
                float(total_amount)
            )
        )

        booking_id = cursor.lastrowid

        # 10. Save individual seat details
        for item in ticket_details:

            connection.execute(
                """
                INSERT INTO booking_seats (
                    booking_id,
                    seat_id,
                    ticket_price,
                    gst_amount,
                    convenience_fee
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    item["seat_id"],
                    item["ticket_price"],
                    item["gst_amount"],
                    float(fee_per_ticket)
                )
            )

        # 11. Convert active holds into booked holds
        connection.execute(
            f"""
            UPDATE seat_holds
            SET status = 'BOOKED'
            WHERE customer_id = ?
              AND show_id = ?
              AND seat_id IN ({placeholders})
              AND status = 'ACTIVE'
            """,
            (customer_id, show_id, *seat_ids)
        )

        # 12. Award loyalty points
        # BR-09: 1 point per Rs.10 of ticket price,
        # excluding GST and convenience fees.

        eligible_amount = sum(
            Decimal(str(item["ticket_price"]))
            for item in ticket_details
        )

        earned_points = int(
            eligible_amount // Decimal("10")
        )

        connection.execute(
            """
            UPDATE customers
            SET loyalty_points = loyalty_points + ?
            WHERE customer_id = ?
            """,
            (earned_points, customer_id)
        )

        # 13. Commit transaction
        connection.commit()

        return {
            "booking_id": booking_id,
            "customer_id": customer_id,
            "show_id": show_id,
            "seats": ticket_details,
            "ticket_total": round(float(ticket_total), 2),
            "convenience_fee": fees["convenience_fee"],
            "convenience_gst": fees["convenience_gst"],
            "total_amount": round(float(total_amount), 2),
            "loyalty_points_earned": earned_points,
            "status": "CONFIRMED"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()