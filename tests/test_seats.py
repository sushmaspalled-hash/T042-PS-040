import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services import seat_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create an isolated database for every test."""

    db_path = tmp_path / "test_cinema.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")

    schema_path = (
        Path(__file__).resolve().parents[1]
        / "database"
        / "schema.sql"
    )

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

    for number in range(1, 13):
        tier = "RECLINER" if number <= 3 else "PRIME"

        connection.execute(
            """
            INSERT INTO seats
                (screen_id, row_name, seat_number, tier)
            VALUES (?, ?, ?, ?)
            """,
            (1, "A", number, tier)
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
        (
            1, "Test Movie",
            (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            300, 150, 100, 0, 0, "ACTIVE"
        )
    )

    connection.execute(
        "INSERT INTO customers (customer_name) VALUES (?)",
        ("Customer One",)
    )

    connection.execute(
        "INSERT INTO customers (customer_name) VALUES (?)",
        ("Customer Two",)
    )

    connection.commit()
    connection.close()

    def test_connection():
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    monkeypatch.setattr(
        seat_service,
        "get_connection",
        test_connection
    )

    return db_path


# Test 1: Get all seats

def test_get_all_seats(test_db):
    seats = seat_service.get_all_seats(1)

    assert len(seats) == 12


# Test 2: All seats initially available

def test_all_seats_initially_available(test_db):
    seats = seat_service.get_available_seats(1)

    assert len(seats) == 12


# Test 3: Hold two seats

def test_hold_two_seats(test_db):
    result = seat_service.hold_seats(1, 1, [1, 2])

    assert result["status"] == "ACTIVE"
    assert result["seat_ids"] == [1, 2]


# Test 4: Held seats are unavailable

def test_held_seats_not_available(test_db):
    seat_service.hold_seats(1, 1, [1, 2])

    available = seat_service.get_available_seats(1)
    available_ids = [seat[0] for seat in available]

    assert 1 not in available_ids
    assert 2 not in available_ids


# Test 5: Another customer cannot hold the same seats

def test_other_customer_cannot_hold_same_seats(test_db):
    seat_service.hold_seats(1, 1, [1, 2])

    with pytest.raises(ValueError):
        seat_service.hold_seats(2, 1, [1, 2])


# Test 6: Empty selection rejected

def test_empty_seat_selection(test_db):
    with pytest.raises(ValueError):
        seat_service.hold_seats(1, 1, [])


# Test 7: More than 10 seats rejected

def test_more_than_ten_seats_rejected(test_db):
    with pytest.raises(ValueError):
        seat_service.hold_seats(
            1, 1, list(range(1, 12))
        )


# Test 8: Duplicate seat IDs rejected

def test_duplicate_seats_rejected(test_db):
    with pytest.raises(ValueError):
        seat_service.hold_seats(1, 1, [1, 1])


# Test 9: Invalid customer rejected

def test_invalid_customer_rejected(test_db):
    with pytest.raises(ValueError):
        seat_service.hold_seats(99, 1, [1])


# Test 10: Invalid seat rejected

def test_invalid_seat_rejected(test_db):
    with pytest.raises(ValueError):
        seat_service.hold_seats(1, 1, [999])


# Test 11: Manually release held seats

def test_release_hold(test_db):
    seat_service.hold_seats(1, 1, [1, 2])

    released = seat_service.release_hold(1, 1)

    assert released == 2

    available = seat_service.get_available_seats(1)

    assert len(available) == 12


# Test 12: Expired holds are released

def test_expired_hold_is_released(test_db):
    seat_service.hold_seats(1, 1, [1, 2])

    connection = sqlite3.connect(test_db)

    expired_time = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    connection.execute(
        """
        UPDATE seat_holds
        SET expires_at = ?
        WHERE customer_id = 1
        AND show_id = 1
        AND status = 'ACTIVE'
        """,
        (expired_time,)
    )

    connection.commit()
    connection.close()

    released = seat_service.release_expired_holds(1)

    assert released == 2

    available = seat_service.get_available_seats(1)

    assert len(available) == 12


# Test 13: Second hold replaces first hold

def test_second_hold_replaces_first(test_db):
    seat_service.hold_seats(1, 1, [1, 2])

    seat_service.hold_seats(1, 1, [3, 4])

    connection = sqlite3.connect(test_db)

    active_seats = connection.execute(
        """
        SELECT seat_id
        FROM seat_holds
        WHERE customer_id = 1
        AND show_id = 1
        AND status = 'ACTIVE'
        """
    ).fetchall()

    connection.close()

    assert {row[0] for row in active_seats} == {3, 4}