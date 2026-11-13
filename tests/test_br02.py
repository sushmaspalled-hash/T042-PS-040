import sqlite3
import pytest
from pathlib import Path

from database import db
from services import seat_service


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated temporary database for BR-02 tests."""

    database_path = tmp_path / "test_br02.db"

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")

    schema_path = Path("database/schema.sql")
    connection.executescript(
        schema_path.read_text(encoding="utf-8")
    )

    connection.execute(
        "INSERT INTO venues (venue_name, location) VALUES (?, ?)",
        ("Test Cinema", "Bengaluru")
    )

    connection.execute(
        "INSERT INTO screens (venue_id, screen_name) VALUES (?, ?)",
        (1, "Screen 1")
    )

    # Create two rows with six seats each.
    for row in ["A", "B"]:
        for number in range(1, 7):
            connection.execute(
                """
                INSERT INTO seats
                (screen_id, row_name, seat_number, tier)
                VALUES (?, ?, ?, ?)
                """,
                (1, row, number, "CLASSIC")
            )

    connection.execute(
        """
        INSERT INTO shows (
            screen_id, movie_name, start_time,
            base_recliner, base_prime, base_classic,
            is_opening_day, is_a_rated, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (1, "Test Movie", "2027-01-01 18:00:00",
         300, 200, 120, 0, 0, "SCHEDULED")
    )

    connection.execute(
        "INSERT INTO customers (customer_name, loyalty_points) VALUES (?, ?)",
        ("Customer 1", 0)
    )

    connection.execute(
        "INSERT INTO customers (customer_name, loyalty_points) VALUES (?, ?)",
        ("Customer 2", 0)
    )

    connection.commit()
    connection.close()

    def temporary_connection():
        conn = sqlite3.connect(database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    monkeypatch.setattr(
        seat_service,
        "get_connection",
        temporary_connection
    )

    return temporary_connection


def get_seat_id(connection, row, number):
    result = connection.execute(
        """
        SELECT seat_id
        FROM seats
        WHERE row_name = ? AND seat_number = ?
        """,
        (row, number)
    ).fetchone()

    return result[0]


def test_consecutive_seats_allowed(test_database):
    connection = test_database()

    seat_ids = [
        get_seat_id(connection, "A", 3),
        get_seat_id(connection, "A", 4)
    ]

    connection.close()

    result = seat_service.hold_seats(1, 1, seat_ids)

    assert result["status"] == "ACTIVE"


def test_non_consecutive_seats_rejected(test_database):
    connection = test_database()

    seat_ids = [
        get_seat_id(connection, "A", 2),
        get_seat_id(connection, "A", 4)
    ]

    connection.close()

    with pytest.raises(ValueError, match="consecutive"):
        seat_service.hold_seats(1, 1, seat_ids)


def test_different_rows_rejected(test_database):
    connection = test_database()

    seat_ids = [
        get_seat_id(connection, "A", 3),
        get_seat_id(connection, "B", 3)
    ]

    connection.close()

    with pytest.raises(ValueError, match="same row"):
        seat_service.hold_seats(1, 1, seat_ids)


def test_single_seat_at_row_edge_rejected(test_database):
    connection = test_database()

    seat_ids = [
        get_seat_id(connection, "A", 2),
        get_seat_id(connection, "A", 3)
    ]

    connection.close()

    with pytest.raises(ValueError, match="isolated"):
        seat_service.hold_seats(1, 1, seat_ids)


def test_single_seat_between_hold_and_booking_rejected(test_database):
    connection = test_database()

    seat_ids = [
        get_seat_id(connection, "A", 3),
        get_seat_id(connection, "A", 4)
    ]

    booked_seat = get_seat_id(connection, "A", 6)

    connection.execute(
        """
        INSERT INTO bookings (
            customer_id, show_id, booking_time,
            total_amount, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (2, 1, "2026-11-12 10:00:00", 100, "CONFIRMED")
    )

    connection.execute(
        """
        INSERT INTO booking_seats (
            booking_id, seat_id, ticket_price,
            gst_amount, convenience_fee
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, booked_seat, 100, 18, 30)
    )

    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="isolated"):
        seat_service.hold_seats(1, 1, seat_ids)
