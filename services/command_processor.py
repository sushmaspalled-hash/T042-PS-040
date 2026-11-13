import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from database.db import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent
COMMAND_FILE = BASE_DIR / "data" / "T042-PS-040-sample-data" / "commands.txt"
OUTPUT_DIR = BASE_DIR / "output"

TICKET_HEADERS = [
    "booking_id", "show_id", "seat_id", "tier", "base_price",
    "occupancy_pct_frozen", "dynamic_multiplier", "time_adjustment",
    "offer_applied", "offer_discount", "loyalty_discount",
    "ticket_price", "gst_rate", "gst_on_ticket",
    "convenience_fee", "gst_on_fee", "ticket_total"
]

EVENT_HEADERS = [
    "ts", "command", "reference", "result", "reason",
    "refund_amount", "points_earned", "points_reversed",
    "points_credited"
]

SEATMAP_HEADERS = ["show_id", "seat_id", "state", "reference"]


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def write_csv(filename, headers, rows):
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(OUTPUT_DIR / filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class CommandProcessor:

    def __init__(self):
        self.connection = get_connection()
        self.ticket_rows = []
        self.event_rows = []
        self.seatmap_rows = []

    def close(self):
        self.connection.close()

    def add_event(
        self, ts, command, reference, result, reason="",
        refund=0, earned=0, reversed_points=0, credited=0
    ):
        self.event_rows.append({
            "ts": ts,
            "command": command,
            "reference": reference,
            "result": result,
            "reason": reason,
            "refund_amount": f"{money(refund):.2f}",
            "points_earned": earned,
            "points_reversed": reversed_points,
            "points_credited": credited
        })

        self.connection.execute(
            """
            INSERT INTO booking_events
            (ts, command, reference, result, reason, refund_amount,
             points_earned, points_reversed, points_credited)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts, command, reference, result, reason,
                float(money(refund)), earned, reversed_points, credited
            )
        )
        self.connection.commit()

    def get_show(self, show_id):
        return self.connection.execute(
            """
            SELECT s.*, m.certificate
            FROM shows s
            JOIN movies m ON m.movie_id = s.movie_id
            WHERE s.show_id = ?
            """,
            (show_id,)
        ).fetchone()

    def get_screen_id(self, show_id):
        row = self.connection.execute(
            "SELECT screen_id FROM shows WHERE show_id = ?",
            (show_id,)
        ).fetchone()

        return row["screen_id"] if row else None

    def get_seats(self, show_id, seat_ids):
        screen_id = self.get_screen_id(show_id)

        if not screen_id:
            return []

        placeholders = ",".join("?" for _ in seat_ids)

        return self.connection.execute(
            f"""
            SELECT seat_id, row_label, seat_no, tier
            FROM seats
            WHERE screen_id = ?
            AND seat_id IN ({placeholders})
            ORDER BY row_label, seat_no
            """,
            [screen_id] + seat_ids
        ).fetchall()

    def get_occupied_seats(self, show_id, ts):
        rows = self.connection.execute(
            """
            SELECT seat_id
            FROM presold_seats
            WHERE show_id = ?
            """,
            (show_id,)
        ).fetchall()

        occupied = {row["seat_id"] for row in rows}

        booked = self.connection.execute(
            """
            SELECT bt.seat_id
            FROM booking_tickets bt
            JOIN bookings b ON b.booking_id = bt.booking_id
            WHERE b.show_id = ?
            AND b.status = 'CONFIRMED'
            """,
            (show_id,)
        ).fetchall()

        occupied.update(row["seat_id"] for row in booked)

        held = self.connection.execute(
            """
            SELECT seat_id
            FROM seat_holds
            WHERE show_id = ?
            AND status = 'ACTIVE'
            AND expires_at > ?
            """,
            (show_id, ts)
        ).fetchall()

        occupied.update(row["seat_id"] for row in held)

        return occupied

    def occupancy(self, show_id, ts):
        screen_id = self.get_screen_id(show_id)

        total = self.connection.execute(
            "SELECT COUNT(*) FROM seats WHERE screen_id = ?",
            (screen_id,)
        ).fetchone()[0]

        occupied = self.get_occupied_seats(show_id, ts)

        if total == 0:
            return 0.0

        return len(occupied) / total * 100

    def validate_seats(self, show_id, seat_ids, ts):
        if not seat_ids:
            return False, "No seats selected"

        if len(seat_ids) > 10:
            return False, "Maximum 10 seats allowed"

        if len(set(seat_ids)) != len(seat_ids):
            return False, "Duplicate seats selected"

        seats = self.get_seats(show_id, seat_ids)

        if len(seats) != len(seat_ids):
            return False, "Invalid seat selection"

        occupied = self.get_occupied_seats(show_id, ts)

        for seat_id in seat_ids:
            if seat_id in occupied:
                return False, f"Seat {seat_id} is unavailable"

        if 2 <= len(seats) <= 4:
            rows = {}

            for seat in seats:
                rows.setdefault(seat["row_label"], []).append(
                    seat["seat_no"]
                )

            if len(rows) != 1:
                return False, "Seats must be in one row"

            numbers = sorted(next(iter(rows.values())))

            if numbers != list(range(numbers[0], numbers[-1] + 1)):
                return False, "Seats must be consecutive"

            row_label = next(iter(rows))

            all_row_seats = self.connection.execute(
                """
                SELECT seat_no, seat_id
                FROM seats
                WHERE screen_id = ?
                AND row_label = ?
                ORDER BY seat_no
                """,
                (self.get_screen_id(show_id), row_label)
            ).fetchall()

            selected = set(seat_ids)
            occupied_set = occupied | selected

            for row_seat in all_row_seats:
                seat_id = row_seat["seat_id"]
                seat_no = row_seat["seat_no"]

                if seat_id in selected:
                    continue

                if seat_id in occupied_set:
                    continue

                has_left_neighbor = any(
                    item["seat_no"] == seat_no - 1
                    for item in all_row_seats
                )
                has_right_neighbor = any(
                    item["seat_no"] == seat_no + 1
                    for item in all_row_seats
                )

                left_occupied = any(
                    item["seat_no"] == seat_no - 1
                    and item["seat_id"] in occupied_set
                    for item in all_row_seats
                )

                right_occupied = any(
                    item["seat_no"] == seat_no + 1
                    and item["seat_id"] in occupied_set
                    for item in all_row_seats
                )

                isolated_between_occupied = left_occupied and right_occupied
                isolated_at_left_edge = not has_left_neighbor and right_occupied
                isolated_at_right_edge = not has_right_neighbor and left_occupied

                if (
                    isolated_between_occupied
                    or isolated_at_left_edge
                    or isolated_at_right_edge
                ):
                    return False, "Selection leaves an isolated empty seat"

        return True, "Seats available"

    def release_expired(self, ts):
        expired = self.connection.execute(
            """
            SELECT DISTINCT hold_id
            FROM seat_holds
            WHERE status = 'ACTIVE'
            AND expires_at <= ?
            """,
            (ts,)
        ).fetchall()

        for row in expired:
            hold_id = row["hold_id"]

            self.connection.execute(
                """
                UPDATE seat_holds
                SET status = 'EXPIRED'
                WHERE hold_id = ?
                """,
                (hold_id,)
            )

            expiry_time = (
                parse_time(
                    self.connection.execute(
                        """
                        SELECT held_at FROM seat_holds
                        WHERE hold_id = ?
                        LIMIT 1
                        """,
                        (hold_id,)
                    ).fetchone()["held_at"]
                ) + timedelta(minutes=8)
            ).strftime("%Y-%m-%d %H:%M:%S")

            self.add_event(
                expiry_time, "HOLD", hold_id, "EXPIRED",
                "Hold expired after 8 minutes"
            )

        self.connection.commit()

    def hold(self, parts):
        _, hold_id, ts, user_id, show_id, seats_text = parts

        self.release_expired(ts)

        seat_ids = [seat.strip() for seat in seats_text.split(",") if seat.strip()]

        show = self.get_show(show_id)

        if not show:
            self.add_event(ts, "HOLD", hold_id, "REJECTED", "Show not found")
            return

        user = self.connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not user:
            self.add_event(ts, "HOLD", hold_id, "REJECTED", "User not found")
            return

        valid, reason = self.validate_seats(show_id, seat_ids, ts)

        if not valid:
            self.add_event(ts, "HOLD", hold_id, "REJECTED", reason)
            return

        # A user's second hold on the same show cancels the first.
        previous = self.connection.execute(
            """
            SELECT DISTINCT hold_id
            FROM seat_holds
            WHERE user_id = ?
            AND show_id = ?
            AND status = 'ACTIVE'
            """,
            (user_id, show_id)
        ).fetchall()

        for row in previous:
            self.connection.execute(
                """
                UPDATE seat_holds
                SET status = 'RELEASED'
                WHERE hold_id = ?
                """,
                (row["hold_id"],)
            )

        occupancy = self.occupancy(show_id, ts)

        # Reuse the frozen occupancy when recliner seats are re-held
        # within the same minute after release.
        previous_recliner = self.connection.execute(
            """
            SELECT occupancy_pct_frozen, held_at
            FROM seat_holds
            WHERE show_id = ?
            AND seat_id IN (
                SELECT seat_id FROM seats
                WHERE screen_id = ? AND tier = 'RECLINER'
            )
            AND status = 'RELEASED'
            ORDER BY held_at DESC
            """,
            (show_id, show["screen_id"])
        ).fetchall()

        for old in previous_recliner:
            old_time = parse_time(old["held_at"])
            new_time = parse_time(ts)

            if old_time.strftime("%Y-%m-%d %H:%M") == new_time.strftime("%Y-%m-%d %H:%M"):
                occupancy = old["occupancy_pct_frozen"]
                break

        expires_at = (
            parse_time(ts) + timedelta(minutes=8)
        ).strftime("%Y-%m-%d %H:%M:%S")

        for seat_id in seat_ids:
            self.connection.execute(
                """
                INSERT INTO seat_holds
                (hold_id, user_id, show_id, seat_id, held_at,
                 expires_at, occupancy_pct_frozen, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (
                    hold_id, user_id, show_id, seat_id,
                    ts, expires_at, occupancy
                )
            )

        self.connection.commit()

        self.add_event(ts, "HOLD", hold_id, "OK", "Seats held successfully")

    def release(self, parts):
        _, hold_id, ts = parts

        self.release_expired(ts)

        row = self.connection.execute(
            """
            SELECT DISTINCT hold_id
            FROM seat_holds
            WHERE hold_id = ?
            AND status = 'ACTIVE'
            """,
            (hold_id,)
        ).fetchone()

        if not row:
            self.add_event(ts, "RELEASE", hold_id, "REJECTED", "Active hold not found")
            return

        self.connection.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE hold_id = ?
            """,
            (hold_id,)
        )

        self.connection.commit()

        self.add_event(ts, "RELEASE", hold_id, "OK", "Hold released")

    def calculate_ticket(self, show, seat, occupancy, booking_time, count, group_discount):
        tier = seat["tier"]

        if tier == "CLASSIC":
            base = Decimal(str(show["base_price_classic"]))
        elif tier == "PRIME":
            base = Decimal(str(show["base_price_prime"]))
        else:
            base = Decimal(str(show["base_price_recliner"]))

        if occupancy < 50:
            multiplier = Decimal("1.00")
        elif occupancy < 80:
            multiplier = Decimal("1.15")
        else:
            multiplier = Decimal("1.30")

        price = money(base * multiplier)

        show_time = parse_time(show["start_ts"])
        hold_time = parse_time(booking_time)

        time_adjustment = "NONE"

        # Opening day takes priority over the last-two-hours discount.
        movie = self.connection.execute(
            """
            SELECT release_date FROM movies WHERE movie_id = ?
            """,
            (show["movie_id"],)
        ).fetchone()

        opening_day = (
            movie and movie["release_date"]
            and show_time.date() == datetime.strptime(
                movie["release_date"], "%Y-%m-%d"
            ).date()
        )

        if opening_day:
            price = money(price * Decimal("1.20"))
            time_adjustment = "OPENING_DAY"

        elif (
            tier == "CLASSIC"
            and timedelta(0) <= show_time - hold_time <= timedelta(hours=2)
        ):
            price = money(price * Decimal("0.90"))
            time_adjustment = "LAST_2H"

        group_amount = Decimal("0")
        matinee_amount = Decimal("0")
        offer = "NONE"

        if count >= 6:
            group_amount = money(price * Decimal("0.10"))

        if (
            tier in ("CLASSIC", "PRIME")
            and show_time.hour < 12
            and show_time.weekday() < 5
        ):
            matinee_amount = Decimal("50.00")

        if group_amount >= matinee_amount and group_amount > 0:
            discount = group_amount
            offer = "GROUP"
        elif matinee_amount > 0:
            discount = min(matinee_amount, price)
            offer = "MATINEE"
        else:
            discount = Decimal("0")

        price = max(Decimal("0"), price - discount)

        return {
            "base": money(base),
            "multiplier": multiplier,
            "time_adjustment": time_adjustment,
            "offer": offer,
            "offer_discount": money(discount),
            "price": money(price)
        }

    def book(self, parts):
        _, booking_id, ts, hold_id, payment_mode, points_text, ages_text = parts

        self.release_expired(ts)

        hold_rows = self.connection.execute(
            """
            SELECT *
            FROM seat_holds
            WHERE hold_id = ?
            AND status = 'ACTIVE'
            """,
            (hold_id,)
        ).fetchall()

        if not hold_rows:
            self.add_event(ts, "BOOK", booking_id, "REJECTED", "Active hold not found or expired")
            return

        hold = hold_rows[0]
        show_id = hold["show_id"]
        user_id = hold["user_id"]

        if any(row["expires_at"] <= ts for row in hold_rows):
            self.add_event(ts, "BOOK", booking_id, "REJECTED", "Hold expired")
            return

        show = self.get_show(show_id)

        seats = self.get_seats(
            show_id, [row["seat_id"] for row in hold_rows]
        )

        ages = []
        if ages_text.strip():
            try:
                ages = [int(age.strip()) for age in ages_text.split(",")]
            except ValueError:
                self.add_event(ts, "BOOK", booking_id, "REJECTED", "Invalid holder ages")
                return

        if show["certificate"] == "A":
            if len(ages) != len(seats) or any(age < 18 for age in ages):
                self.add_event(ts, "BOOK", booking_id, "REJECTED", "A-rated shows require every holder to be at least 18")
                return

        occupancy = hold["occupancy_pct_frozen"]
        group_discount = len(seats) >= 6

        calculations = []

        for seat in seats:
            calculations.append(
                self.calculate_ticket(
                    show, seat, occupancy, ts,
                    len(seats), group_discount
                )
            )

        subtotal = sum(
            (item["price"] for item in calculations),
            Decimal("0")
        )

        requested_points = int(points_text or 0)

        user = self.connection.execute(
            "SELECT loyalty_points FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        available_points = user["loyalty_points"]

        if requested_points < 0 or requested_points > available_points:
            self.add_event(ts, "BOOK", booking_id, "REJECTED", "Insufficient loyalty points")
            return

        if requested_points % 100 != 0:
            self.add_event(ts, "BOOK", booking_id, "REJECTED", "Points redemption must be in multiples of 100")
            return

        requested_discount = Decimal(requested_points // 100) * Decimal("50")
        max_discount = money(subtotal * Decimal("0.50"))
        loyalty_discount = min(requested_discount, max_discount)

        if requested_discount > max_discount:
            requested_points = int(max_discount // Decimal("50")) * 100
            loyalty_discount = Decimal(requested_points // 100) * Decimal("50")

        discount_remaining = loyalty_discount

        fee = Decimal("30") if len(seats) <= 2 else Decimal("25")

        ticket_total = Decimal("0")
        earned_points = 0

        for seat, calculation in zip(seats, calculations):
            original_price = calculation["price"]

            seat_discount = min(original_price, discount_remaining)
            discount_remaining -= seat_discount

            final_price = money(original_price - seat_discount)

            gst_rate = Decimal("0.12") if final_price <= 100 else Decimal("0.18")
            gst_ticket = money(final_price * gst_rate)

            convenience_fee = fee
            gst_fee = money(convenience_fee * Decimal("0.18"))

            total = money(final_price + gst_ticket + convenience_fee + gst_fee)
            ticket_total += total

            earned_points += int(final_price // 10)

            self.ticket_rows.append({
                "booking_id": booking_id,
                "show_id": show_id,
                "seat_id": seat["seat_id"],
                "tier": seat["tier"],
                "base_price": f"{calculation['base']:.2f}",
                "occupancy_pct_frozen": f"{occupancy:.2f}",
                "dynamic_multiplier": f"{calculation['multiplier']:.2f}",
                "time_adjustment": calculation["time_adjustment"],
                "offer_applied": calculation["offer"],
                "offer_discount": f"{calculation['offer_discount']:.2f}",
                "loyalty_discount": f"{seat_discount:.2f}",
                "ticket_price": f"{final_price:.2f}",
                "gst_rate": f"{gst_rate:.2f}",
                "gst_on_ticket": f"{gst_ticket:.2f}",
                "convenience_fee": f"{convenience_fee:.2f}",
                "gst_on_fee": f"{gst_fee:.2f}",
                "ticket_total": f"{total:.2f}"
            })

            self.connection.execute(
                """
                INSERT INTO booking_tickets
                (ticket_id, booking_id, show_id, seat_id, tier,
                 base_price, occupancy_pct_frozen, dynamic_multiplier,
                 time_adjustment, offer_applied, offer_discount,
                 loyalty_discount, ticket_price, gst_rate,
                 gst_on_ticket, convenience_fee, gst_on_fee, ticket_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{booking_id}-{seat['seat_id']}",
                    booking_id, show_id, seat["seat_id"], seat["tier"],
                    float(calculation["base"]), occupancy,
                    float(calculation["multiplier"]),
                    calculation["time_adjustment"],
                    calculation["offer"],
                    float(calculation["offer_discount"]),
                    float(seat_discount),
                    float(final_price), float(gst_rate),
                    float(gst_ticket), float(convenience_fee),
                    float(gst_fee), float(total)
                )
            )

        self.connection.execute(
            """
            INSERT INTO bookings
            (booking_id, user_id, show_id, booking_ts,
             payment_method, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED')
            """,
            (
                booking_id, user_id, show_id, ts,
                payment_mode, float(money(ticket_total))
            )
        )

        self.connection.execute(
            """
            UPDATE seat_holds
            SET status = 'BOOKED'
            WHERE hold_id = ?
            """,
            (hold_id,)
        )

        self.connection.execute(
            """
            UPDATE users
            SET loyalty_points = loyalty_points - ? + ?
            WHERE user_id = ?
            """,
            (requested_points, earned_points, user_id)
        )

        self.connection.commit()

        self.add_event(
            ts, "BOOK", booking_id, "OK",
            "Booking confirmed",
            earned=earned_points
        )

    def cancel(self, parts):
        _, booking_id, ts = parts

        booking = self.connection.execute(
            """
            SELECT b.*, s.start_ts
            FROM bookings b
            JOIN shows s ON s.show_id = b.show_id
            WHERE b.booking_id = ?
            """,
            (booking_id,)
        ).fetchone()

        if not booking or booking["status"] != "CONFIRMED":
            self.add_event(ts, "CANCEL", booking_id, "REJECTED", "Booking not found or already cancelled")
            return

        tickets = self.connection.execute(
            """
            SELECT ticket_price, ticket_total
            FROM booking_tickets
            WHERE booking_id = ?
            """,
            (booking_id,)
        ).fetchall()

        ticket_price_total = sum(
            (Decimal(str(row["ticket_price"])) for row in tickets),
            Decimal("0")
        )

        cancel_time = parse_time(ts)
        show_time = parse_time(booking["start_ts"])
        remaining = show_time - cancel_time

        if remaining > timedelta(hours=4):
            refund_rate = Decimal("0.75")
        elif remaining >= timedelta(hours=2):
            refund_rate = Decimal("0.50")
        else:
            refund_rate = Decimal("0")

        refund = money(ticket_price_total * refund_rate)

        user_id = booking["user_id"]

        earned = self.connection.execute(
            """
            SELECT COALESCE(SUM(points_earned), 0)
            FROM booking_events
            WHERE reference = ?
            AND command = 'BOOK'
            """,
            (booking_id,)
        ).fetchone()[0]

        self.connection.execute(
            """
            UPDATE users
            SET loyalty_points = loyalty_points - ?
            WHERE user_id = ?
            """,
            (earned, user_id)
        )

        self.connection.execute(
            """
            UPDATE bookings
            SET status = 'CANCELLED'
            WHERE booking_id = ?
            """,
            (booking_id,)
        )

        self.connection.commit()

        self.add_event(
            ts, "CANCEL", booking_id, "OK",
            "Booking cancelled",
            refund=refund,
            reversed_points=earned
        )

    def cancel_show(self, parts):
        _, show_id, ts = parts

        bookings = self.connection.execute(
            """
            SELECT booking_id, user_id
            FROM bookings
            WHERE show_id = ?
            AND status = 'CONFIRMED'
            """,
            (show_id,)
        ).fetchall()

        total_refund = Decimal("0")
        total_credited = 0

        for booking in bookings:
            booking_id = booking["booking_id"]
            user_id = booking["user_id"]

            tickets = self.connection.execute(
                """
                SELECT ticket_total
                FROM booking_tickets
                WHERE booking_id = ?
                """,
                (booking_id,)
            ).fetchall()

            refund = sum(
                (Decimal(str(row["ticket_total"])) for row in tickets),
                Decimal("0")
            )

            earned = self.connection.execute(
                """
                SELECT COALESCE(SUM(points_earned), 0)
                FROM booking_events
                WHERE reference = ?
                AND command = 'BOOK'
                """,
                (booking_id,)
            ).fetchone()[0]

            credit = earned * 2

            self.connection.execute(
                """
                UPDATE users
                SET loyalty_points = loyalty_points - ? + ?
                WHERE user_id = ?
                """,
                (earned, credit, user_id)
            )

            self.connection.execute(
                """
                UPDATE bookings
                SET status = 'CANCELLED'
                WHERE booking_id = ?
                """,
                (booking_id,)
            )

            total_refund += refund
            total_credited += credit

        self.connection.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE show_id = ?
            AND status = 'ACTIVE'
            """,
            (show_id,)
        )

        self.connection.commit()

        self.add_event(
            ts, "CANCEL_SHOW", show_id, "OK",
            "Show cancelled by venue",
            refund=total_refund,
            credited=total_credited
        )

    def print_invoice(self, parts):
        _, booking_id = parts

        rows = self.connection.execute(
            """
            SELECT *
            FROM booking_tickets
            WHERE booking_id = ?
            ORDER BY seat_id
            """,
            (booking_id,)
        ).fetchall()

        if not rows:
            print(f"Invoice not found for booking: {booking_id}")
            return

        print(f"\\nINVOICE: {booking_id}")
        print("-" * 60)

        for row in rows:
            print(
                f"Seat: {row['seat_id']} | Tier: {row['tier']} | "
                f"Ticket: ₹{row['ticket_price']:.2f} | "
                f"GST: ₹{row['gst_on_ticket']:.2f} | "
                f"Fee: ₹{row['convenience_fee']:.2f} | "
                f"Fee GST: ₹{row['gst_on_fee']:.2f} | "
                f"Total: ₹{row['ticket_total']:.2f}"
            )

        invoice_total = sum(
            (Decimal(str(row["ticket_total"])) for row in rows),
            Decimal("0")
        )
        print("-" * 60)
        print(f"Invoice total: ₹{money(invoice_total):.2f}")

    def print_seatmap(self, parts):
        _, show_id = parts

        screen_id = self.get_screen_id(show_id)

        seats = self.connection.execute(
            """
            SELECT seat_id
            FROM seats
            WHERE screen_id = ?
            ORDER BY row_label, seat_no
            """,
            (screen_id,)
        ).fetchall()

        for seat in seats:
            seat_id = seat["seat_id"]

            presold = self.connection.execute(
                """
                SELECT booking_ref
                FROM presold_seats
                WHERE show_id = ? AND seat_id = ?
                """,
                (show_id, seat_id)
            ).fetchone()

            if presold:
                state = "PRESOLD"
                reference = presold["booking_ref"]
            else:
                booked = self.connection.execute(
                    """
                    SELECT b.booking_id
                    FROM booking_tickets bt
                    JOIN bookings b ON b.booking_id = bt.booking_id
                    WHERE b.show_id = ?
                    AND bt.seat_id = ?
                    AND b.status = 'CONFIRMED'
                    """,
                    (show_id, seat_id)
                ).fetchone()

                if booked:
                    state = "BOOKED"
                    reference = booked["booking_id"]
                else:
                    held = self.connection.execute(
                        """
                        SELECT hold_id
                        FROM seat_holds
                        WHERE show_id = ?
                        AND seat_id = ?
                        AND status = 'ACTIVE'
                        ORDER BY held_at DESC
                        LIMIT 1
                        """,
                        (show_id, seat_id)
                    ).fetchone()

                    if held:
                        state = "HELD"
                        reference = held["hold_id"]
                    else:
                        state = "FREE"
                        reference = ""

            self.seatmap_rows.append({
                "show_id": show_id,
                "seat_id": seat_id,
                "state": state,
                "reference": reference
            })

    def process_file(self):
        if not COMMAND_FILE.exists():
            raise FileNotFoundError(
                f"Command file not found: {COMMAND_FILE}"
            )

        with open(COMMAND_FILE, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split("|")
                command = parts[0]

                try:
                    if command == "HOLD":
                        self.hold(parts)

                    elif command == "RELEASE":
                        self.release(parts)

                    elif command == "BOOK":
                        self.book(parts)

                    elif command == "CANCEL":
                        self.cancel(parts)

                    elif command == "CANCEL_SHOW":
                        self.cancel_show(parts)

                    elif command == "PRINT_INVOICE":
                        self.print_invoice(parts)

                    elif command == "PRINT_SEATMAP":
                        self.print_seatmap(parts)

                    else:
                        print(f"Unknown command at line {line_number}: {command}")

                except Exception as error:
                    print(
                        f"Error at line {line_number}: {line}\n"
                        f"Reason: {error}"
                    )
                    raise

        write_csv("ticket_lines.csv", TICKET_HEADERS, self.ticket_rows)
        write_csv("booking_events.csv", EVENT_HEADERS, self.event_rows)
        write_csv("seat_maps.csv", SEATMAP_HEADERS, self.seatmap_rows)

        print("\nCommand processing completed.")
        print(f"Ticket lines generated: {len(self.ticket_rows)}")
        print(f"Booking events generated: {len(self.event_rows)}")
        print(f"Seat map rows generated: {len(self.seatmap_rows)}")
        print(f"Output folder: {OUTPUT_DIR}")


def main():
    processor = CommandProcessor()

    try:
        processor.process_file()
    finally:
        processor.close()


if __name__ == "__main__":
    main()