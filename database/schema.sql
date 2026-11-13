PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_name TEXT NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS screens (
    screen_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL,
    screen_name TEXT NOT NULL,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
);

CREATE TABLE IF NOT EXISTS seats (
    seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL,
    row_name TEXT NOT NULL,
    seat_number INTEGER NOT NULL,
    tier TEXT NOT NULL CHECK (
        tier IN ('RECLINER', 'PRIME', 'CLASSIC')
    ),
    FOREIGN KEY (screen_id) REFERENCES screens(screen_id),
    UNIQUE (screen_id, row_name, seat_number)
);

CREATE TABLE IF NOT EXISTS shows (
    show_id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL,
    movie_name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    base_recliner REAL NOT NULL,
    base_prime REAL NOT NULL,
    base_classic REAL NOT NULL,
    is_opening_day INTEGER DEFAULT 0,
    is_a_rated INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    FOREIGN KEY (screen_id) REFERENCES screens(screen_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    loyalty_points INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seat_holds (
    hold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL,
    seat_id INTEGER NOT NULL,
    held_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    frozen_occupancy REAL NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (show_id) REFERENCES shows(show_id),
    FOREIGN KEY (seat_id) REFERENCES seats(seat_id)
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL,
    booking_time TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'CONFIRMED',
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (show_id) REFERENCES shows(show_id)
);

CREATE TABLE IF NOT EXISTS booking_seats (
    booking_seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    seat_id INTEGER NOT NULL,
    ticket_price REAL NOT NULL,
    gst_amount REAL NOT NULL,
    convenience_fee REAL NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (seat_id) REFERENCES seats(seat_id)
);