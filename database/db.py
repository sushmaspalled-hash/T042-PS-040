import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "official_cinema.db"

RUNTIME_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    show_id TEXT NOT NULL,
    booking_ts TEXT NOT NULL,
    payment_method TEXT,
    total_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'CONFIRMED'
);

CREATE TABLE IF NOT EXISTS booking_tickets (
    ticket_id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL,
    show_id TEXT NOT NULL,
    seat_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    base_price REAL NOT NULL,
    occupancy_pct_frozen REAL NOT NULL,
    dynamic_multiplier REAL NOT NULL,
    time_adjustment TEXT,
    offer_applied TEXT,
    offer_discount REAL DEFAULT 0,
    loyalty_discount REAL DEFAULT 0,
    ticket_price REAL NOT NULL,
    gst_rate REAL NOT NULL,
    gst_on_ticket REAL NOT NULL,
    convenience_fee REAL NOT NULL,
    gst_on_fee REAL NOT NULL,
    ticket_total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS booking_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    command TEXT NOT NULL,
    reference TEXT,
    result TEXT NOT NULL,
    reason TEXT,
    refund_amount REAL DEFAULT 0,
    points_earned INTEGER DEFAULT 0,
    points_reversed INTEGER DEFAULT 0,
    points_credited INTEGER DEFAULT 0
);
"""


def migrate_seat_holds(connection):
    columns = connection.execute(
        "PRAGMA table_info(seat_holds)"
    ).fetchall()

    if not columns:
        connection.execute("""
            CREATE TABLE seat_holds (
                hold_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                show_id TEXT NOT NULL,
                seat_id TEXT NOT NULL,
                held_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                occupancy_pct_frozen REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                PRIMARY KEY (hold_id, seat_id)
            )
        """)
        return

    primary_keys = {
        row["name"]: row["pk"] for row in columns
    }

    if (
        primary_keys.get("hold_id") == 1
        and primary_keys.get("seat_id") == 2
    ):
        return

    connection.execute(
        "ALTER TABLE seat_holds RENAME TO seat_holds_old"
    )

    connection.execute("""
        CREATE TABLE seat_holds (
            hold_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            show_id TEXT NOT NULL,
            seat_id TEXT NOT NULL,
            held_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            occupancy_pct_frozen REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            PRIMARY KEY (hold_id, seat_id)
        )
    """)

    connection.execute("""
        INSERT INTO seat_holds
        SELECT hold_id, user_id, show_id, seat_id,
               held_at, expires_at, occupancy_pct_frozen, status
        FROM seat_holds_old
    """)

    connection.execute("DROP TABLE seat_holds_old")


def migrate_booking_tickets(connection):
    columns = connection.execute(
        "PRAGMA table_info(booking_tickets)"
    ).fetchall()

    if not columns:
        return

    ticket_id_column = next(
        (row for row in columns if row["name"] == "ticket_id"),
        None
    )

    if ticket_id_column and ticket_id_column["type"].upper() == "TEXT":
        return

    connection.execute(
        "ALTER TABLE booking_tickets RENAME TO booking_tickets_old"
    )

    connection.execute("""
        CREATE TABLE booking_tickets (
            ticket_id TEXT PRIMARY KEY,
            booking_id TEXT NOT NULL,
            show_id TEXT NOT NULL,
            seat_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            base_price REAL NOT NULL,
            occupancy_pct_frozen REAL NOT NULL,
            dynamic_multiplier REAL NOT NULL,
            time_adjustment TEXT,
            offer_applied TEXT,
            offer_discount REAL DEFAULT 0,
            loyalty_discount REAL DEFAULT 0,
            ticket_price REAL NOT NULL,
            gst_rate REAL NOT NULL,
            gst_on_ticket REAL NOT NULL,
            convenience_fee REAL NOT NULL,
            gst_on_fee REAL NOT NULL,
            ticket_total REAL NOT NULL
        )
    """)

    connection.execute("""
        INSERT INTO booking_tickets (
            ticket_id, booking_id, show_id, seat_id, tier,
            base_price, occupancy_pct_frozen, dynamic_multiplier,
            time_adjustment, offer_applied, offer_discount,
            loyalty_discount, ticket_price, gst_rate,
            gst_on_ticket, convenience_fee, gst_on_fee, ticket_total
        )
        SELECT
            CAST(ticket_id AS TEXT), booking_id, show_id, seat_id, tier,
            base_price, occupancy_pct_frozen, dynamic_multiplier,
            time_adjustment, offer_applied, offer_discount,
            loyalty_discount, ticket_price, gst_rate,
            gst_on_ticket, convenience_fee, gst_on_fee, ticket_total
        FROM booking_tickets_old
    """)

    connection.execute("DROP TABLE booking_tickets_old")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    migrate_seat_holds(connection)
    migrate_booking_tickets(connection)

    connection.executescript(RUNTIME_SCHEMA)

    return connection


def initialize_database():
    connection = get_connection()

    try:
        connection.commit()
        print("Official database connected successfully!")
        print("Ticketing tables initialized successfully!")
        print("Database migrations completed!")
        print(f"Database: {DB_PATH}")

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()