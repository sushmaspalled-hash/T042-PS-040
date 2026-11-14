import sqlite3
import pytest

from services.command_processor import CommandProcessor


@pytest.fixture
def processor():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript("""
        CREATE TABLE shows (
            show_id INTEGER PRIMARY KEY,
            screen_id INTEGER
        );

        CREATE TABLE seats (
            seat_id INTEGER PRIMARY KEY,
            screen_id INTEGER,
            row_label TEXT,
            seat_no INTEGER,
            tier TEXT
        );

        CREATE TABLE presold_seats (
            show_id INTEGER,
            seat_id INTEGER
        );

        CREATE TABLE bookings (
            booking_id INTEGER PRIMARY KEY,
            show_id INTEGER,
            status TEXT
        );

        CREATE TABLE booking_tickets (
            booking_id INTEGER,
            seat_id INTEGER
        );

        CREATE TABLE seat_holds (
            show_id INTEGER,
            seat_id INTEGER,
            status TEXT,
            expires_at TEXT,
            user_id TEXT
        );
    """)

    connection.execute(
        "INSERT INTO shows VALUES (1, 1)"
    )

    # Create two rows with six seats each.
    seat_id = 1

    for row in ["A", "B"]:
        for number in range(1, 7):
            connection.execute(
                """
                INSERT INTO seats
                VALUES (?, 1, ?, ?, 'CLASSIC')
                """,
                (seat_id, row, number)
            )
            seat_id += 1

    connection.commit()

    obj = CommandProcessor.__new__(CommandProcessor)
    obj.connection = connection

    yield obj

    connection.close()


def get_seat(processor, row, number):
    result = processor.connection.execute(
        """
        SELECT seat_id FROM seats
        WHERE row_label = ? AND seat_no = ?
        """,
        (row, number)
    ).fetchone()

    return result["seat_id"]


def test_consecutive_seats_allowed(processor):
    seats = [
        get_seat(processor, "A", 3),
        get_seat(processor, "A", 4)
    ]

    valid, reason = processor.validate_seats(
        1, seats, "2026-11-14 18:00:00"
    )

    assert valid is True


def test_non_consecutive_seats_rejected(processor):
    seats = [
        get_seat(processor, "A", 2),
        get_seat(processor, "A", 4)
    ]

    valid, reason = processor.validate_seats(
        1, seats, "2026-11-14 18:00:00"
    )

    assert valid is False
    assert "consecutive" in reason.lower()


def test_different_rows_rejected(processor):
    seats = [
        get_seat(processor, "A", 3),
        get_seat(processor, "B", 3)
    ]

    valid, reason = processor.validate_seats(
        1, seats, "2026-11-14 18:00:00"
    )

    assert valid is False
    assert "one row" in reason.lower()


def test_isolated_seat_at_row_edge_rejected(processor):
    seats = [
        get_seat(processor, "A", 2),
        get_seat(processor, "A", 3)
    ]

    valid, reason = processor.validate_seats(
        1, seats, "2026-11-14 18:00:00"
    )

    assert valid is False
    assert "isolated" in reason.lower()


def test_isolated_seat_between_hold_and_booked_seat_rejected(processor):
    seats = [
        get_seat(processor, "A", 3),
        get_seat(processor, "A", 4)
    ]

    booked_seat = get_seat(processor, "A", 6)

    connection = processor.connection

    connection.execute(
        "INSERT INTO bookings VALUES (1, 1, 'CONFIRMED')"
    )

    connection.execute(
        "INSERT INTO booking_tickets VALUES (1, ?)",
        (booked_seat,)
    )

    connection.commit()

    valid, reason = processor.validate_seats(
        1, seats, "2026-11-14 18:00:00"
    )

    assert valid is False
    assert "isolated" in reason.lower()