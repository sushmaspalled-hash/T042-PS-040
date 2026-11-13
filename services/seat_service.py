
from datetime import datetime, timedelta, timezone

from database.db import get_connection


# --------------------------------------------------
# TIME MANAGEMENT
# --------------------------------------------------

def current_time():
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# --------------------------------------------------
# RELEASE EXPIRED HOLDS
# --------------------------------------------------

def release_expired_holds(show_id=None):
    """Automatically release expired seat holds."""

    connection = get_connection()

    try:
        now = current_time().isoformat()

        if show_id is None:
            cursor = connection.execute(
                """
                UPDATE seat_holds
                SET status = 'EXPIRED'
                WHERE status = 'ACTIVE'
                AND expires_at <= ?
                """,
                (now,)
            )
        else:
            cursor = connection.execute(
                """
                UPDATE seat_holds
                SET status = 'EXPIRED'
                WHERE show_id = ?
                AND status = 'ACTIVE'
                AND expires_at <= ?
                """,
                (show_id, now)
            )

        connection.commit()
        return cursor.rowcount

    finally:
        connection.close()


# --------------------------------------------------
# GET ALL SEATS
# --------------------------------------------------

def get_all_seats(show_id):
    """Get all seats belonging to a show."""

    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT seat_id, row_name, seat_number, tier
            FROM seats
            WHERE screen_id = (
                SELECT screen_id
                FROM shows
                WHERE show_id = ?
            )
            ORDER BY row_name, seat_number
            """,
            (show_id,)
        ).fetchall()

    finally:
        connection.close()


# --------------------------------------------------
# GET AVAILABLE SEATS
# --------------------------------------------------

def get_available_seats(show_id):
    """Return seats that are neither booked nor actively held."""

    release_expired_holds(show_id)

    connection = get_connection()

    try:
        now = current_time().isoformat()

        return connection.execute(
            """
            SELECT
                s.seat_id,
                s.row_name,
                s.seat_number,
                s.tier
            FROM seats s

            WHERE s.screen_id = (
                SELECT screen_id
                FROM shows
                WHERE show_id = ?
            )

            AND NOT EXISTS (
                SELECT 1
                FROM booking_seats bs
                JOIN bookings b
                    ON b.booking_id = bs.booking_id
                WHERE bs.seat_id = s.seat_id
                AND b.show_id = ?
                AND b.status = 'CONFIRMED'
            )

            AND NOT EXISTS (
                SELECT 1
                FROM seat_holds sh
                WHERE sh.seat_id = s.seat_id
                AND sh.show_id = ?
                AND sh.status = 'ACTIVE'
                AND sh.expires_at > ?
            )

            ORDER BY s.row_name, s.seat_number
            """,
            (show_id, show_id, show_id, now)
        ).fetchall()

    finally:
        connection.close()


# --------------------------------------------------
# CALCULATE SHOW OCCUPANCY
# --------------------------------------------------

def calculate_occupancy(connection, show_id, now):
    """Calculate occupancy percentage."""

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM seats
        WHERE screen_id = (
            SELECT screen_id
            FROM shows
            WHERE show_id = ?
        )
        """,
        (show_id,)
    ).fetchone()[0]

    if total == 0:
        raise ValueError("No seats configured for this show.")

    occupied = connection.execute(
        """
        SELECT COUNT(DISTINCT seat_id)
        FROM (
            SELECT bs.seat_id
            FROM booking_seats bs
            JOIN bookings b
                ON b.booking_id = bs.booking_id
            WHERE b.show_id = ?
            AND b.status = 'CONFIRMED'

            UNION

            SELECT seat_id
            FROM seat_holds
            WHERE show_id = ?
            AND status = 'ACTIVE'
            AND expires_at > ?
        )
        """,
        (show_id, show_id, now)
    ).fetchone()[0]

    return (occupied / total) * 100


# --------------------------------------------------
# BR-02: VALIDATE SEAT SELECTION
# --------------------------------------------------

def validate_seat_selection(connection, show_id, seat_ids, now):
    """
    BR-02:

    1. Groups of 2-4 seats must be contiguous.
    2. Groups of 2-4 seats must be in one row.
    3. Do not leave a single isolated seat at a row edge.
    4. Do not leave a single empty seat between occupied seats.
    """

    if 2 <= len(seat_ids) <= 4:

        placeholders = ",".join("?" for _ in seat_ids)

        selected = connection.execute(
            f"""
            SELECT seat_id, row_name, seat_number
            FROM seats
            WHERE seat_id IN ({placeholders})
            """,
            tuple(seat_ids)
        ).fetchall()

        if len(selected) != len(seat_ids):
            raise ValueError("Invalid seat selection.")

        rows = {seat[1] for seat in selected}

        if len(rows) != 1:
            raise ValueError(
                "BR-02: Select 2-4 seats from the same row."
            )

        numbers = sorted(seat[2] for seat in selected)

        expected = list(
            range(numbers[0], numbers[0] + len(numbers))
        )

        if numbers != expected:
            raise ValueError(
                "BR-02: Selected seats must be consecutive."
            )

    # Check isolated single-seat gaps in affected rows.
    placeholders = ",".join("?" for _ in seat_ids)

    selected_rows = connection.execute(
        f"""
        SELECT DISTINCT row_name
        FROM seats
        WHERE seat_id IN ({placeholders})
        """,
        tuple(seat_ids)
    ).fetchall()

    for row_result in selected_rows:

        row_name = row_result[0]

        row_seats = connection.execute(
            """
            SELECT seat_id, seat_number
            FROM seats
            WHERE screen_id = (
                SELECT screen_id
                FROM shows
                WHERE show_id = ?
            )
            AND row_name = ?
            ORDER BY seat_number
            """,
            (show_id, row_name)
        ).fetchall()

        occupied = set(seat_ids)

        # Existing confirmed bookings.
        booked = connection.execute(
            """
            SELECT bs.seat_id
            FROM booking_seats bs
            JOIN bookings b
                ON b.booking_id = bs.booking_id
            WHERE b.show_id = ?
            AND b.status = 'CONFIRMED'
            """,
            (show_id,)
        ).fetchall()

        occupied.update(seat[0] for seat in booked)

        # Other customers' active holds.
        held = connection.execute(
            """
            SELECT seat_id
            FROM seat_holds
            WHERE show_id = ?
            AND status = 'ACTIVE'
            AND expires_at > ?
            """,
            (show_id, now)
        ).fetchall()

        occupied.update(seat[0] for seat in held)

        row_ids = [seat[0] for seat in row_seats]

        for index, seat_id in enumerate(row_ids):

            if seat_id in occupied:
                continue

            previous_occupied = (
                index > 0 and row_ids[index - 1] in occupied
            )

            next_occupied = (
                index < len(row_ids) - 1
                and row_ids[index + 1] in occupied
            )

            if previous_occupied and next_occupied:
                raise ValueError(
                    "BR-02: Selection leaves one isolated seat."
                )

            if index == 0 and next_occupied:
                raise ValueError(
                    "BR-02: Selection leaves one isolated seat at row edge."
                )

            if index == len(row_ids) - 1 and previous_occupied:
                raise ValueError(
                    "BR-02: Selection leaves one isolated seat at row edge."
                )


# --------------------------------------------------
# HOLD SEATS
# --------------------------------------------------

def hold_seats(customer_id, show_id, seat_ids):
    """
    Create an eight-minute seat hold.

    BR-01:
    - Maximum 10 seats.
    - Second hold replaces previous hold.
    - Expired holds are released.

    BR-02:
    - Consecutive seats.
    - Same-row restriction for 2-4 seats.
    - Prevent isolated single seats.

    BR-03:
    - Freeze occupancy at hold time.
    """

    if not seat_ids:
        raise ValueError("Please select seats.")

    if len(seat_ids) > 10:
        raise ValueError("Maximum 10 seats allowed.")

    if len(set(seat_ids)) != len(seat_ids):
        raise ValueError("Duplicate seats are not allowed.")

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        now = current_time()
        now_text = now.isoformat()
        expiry = (now + timedelta(minutes=8)).isoformat()

        # Validate customer.
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

        # Validate show.
        show = connection.execute(
            """
            SELECT screen_id
            FROM shows
            WHERE show_id = ?
            """,
            (show_id,)
        ).fetchone()

        if show is None:
            raise ValueError("Show not found.")

        # Release expired holds.
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

        # Validate seats belong to the show's screen.
        placeholders = ",".join("?" for _ in seat_ids)

        valid_seats = connection.execute(
            f"""
            SELECT seat_id
            FROM seats
            WHERE screen_id = ?
            AND seat_id IN ({placeholders})
            """,
            (show[0], *seat_ids)
        ).fetchall()

        if len(valid_seats) != len(seat_ids):
            raise ValueError("Invalid seat selection.")

        # Check booked seats before releasing previous holds.
        booked = connection.execute(
            f"""
            SELECT bs.seat_id
            FROM booking_seats bs
            JOIN bookings b
                ON b.booking_id = bs.booking_id
            WHERE b.show_id = ?
            AND b.status = 'CONFIRMED'
            AND bs.seat_id IN ({placeholders})
            """,
            (show_id, *seat_ids)
        ).fetchall()

        if booked:
            raise ValueError("One or more seats are already booked.")

        # Release previous active hold by this customer.
        connection.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE customer_id = ?
            AND show_id = ?
            AND status = 'ACTIVE'
            """,
            (customer_id, show_id)
        )

        # Check seats held by other customers.
        held = connection.execute(
            f"""
            SELECT seat_id
            FROM seat_holds
            WHERE show_id = ?
            AND status = 'ACTIVE'
            AND expires_at > ?
            AND customer_id != ?
            AND seat_id IN ({placeholders})
            """,
            (show_id, now_text, customer_id, *seat_ids)
        ).fetchall()

        if held:
            raise ValueError("One or more seats are currently held.")

        # BR-02 validation.
        validate_seat_selection(
            connection,
            show_id,
            seat_ids,
            now_text
        )

        # BR-03: Calculate occupancy before creating new holds.
        occupancy = calculate_occupancy(
            connection,
            show_id,
            now_text
        )

        # Create holds.
        for seat_id in seat_ids:

            connection.execute(
                """
                INSERT INTO seat_holds (
                    customer_id,
                    show_id,
                    seat_id,
                    held_at,
                    expires_at,
                    frozen_occupancy,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (
                    customer_id,
                    show_id,
                    seat_id,
                    now_text,
                    expiry,
                    occupancy
                )
            )

        connection.commit()

        return {
            "customer_id": customer_id,
            "show_id": show_id,
            "seat_ids": seat_ids,
            "occupancy": occupancy,
            "expires_at": expiry,
            "status": "ACTIVE"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# RELEASE HOLDS MANUALLY
# --------------------------------------------------

def release_hold(customer_id, show_id):
    """Manually release all active holds belonging to a customer."""

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE seat_holds
            SET status = 'RELEASED'
            WHERE customer_id = ?
            AND show_id = ?
            AND status = 'ACTIVE'
            """,
            (customer_id, show_id)
        )

        connection.commit()

        return cursor.rowcount

    finally:
        connection.close()