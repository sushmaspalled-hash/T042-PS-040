import csv
import sqlite3
from pathlib import Path


# ==================================================
# PATH CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "T042-PS-040-sample-data"

DB_PATH = PROJECT_ROOT / "data" / "official_cinema.db"


# ==================================================
# DATABASE SCHEMA
# ==================================================

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE venues (
    venue_id TEXT PRIMARY KEY,
    venue_name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE screens (
    screen_id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL,
    screen_name TEXT NOT NULL,
    total_seats INTEGER NOT NULL,
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
);

CREATE TABLE seats (
    screen_id TEXT NOT NULL,
    seat_id TEXT NOT NULL,
    row_label TEXT NOT NULL,
    seat_no INTEGER NOT NULL,
    tier TEXT NOT NULL,
    PRIMARY KEY (screen_id, seat_id),
    FOREIGN KEY (screen_id) REFERENCES screens(screen_id)
);

CREATE TABLE movies (
    movie_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    certificate TEXT NOT NULL,
    release_date TEXT NOT NULL
);

CREATE TABLE shows (
    show_id TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    movie_id TEXT NOT NULL,
    start_ts TEXT NOT NULL,
    base_price_recliner REAL NOT NULL,
    base_price_prime REAL NOT NULL,
    base_price_classic REAL NOT NULL,
    FOREIGN KEY (screen_id) REFERENCES screens(screen_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    mobile TEXT NOT NULL,
    loyalty_points INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE presold_seats (
    show_id TEXT NOT NULL,
    seat_id TEXT NOT NULL,
    booking_ref TEXT NOT NULL,
    PRIMARY KEY (show_id, seat_id),
    FOREIGN KEY (show_id) REFERENCES shows(show_id)
);
"""


# ==================================================
# EXPECTED CSV COLUMNS
# ==================================================

CSV_CONFIG = {
    "venues.csv": (
        "venues",
        ["venue_id", "venue_name", "city"]
    ),

    "screens.csv": (
        "screens",
        ["screen_id", "venue_id", "screen_name", "total_seats"]
    ),

    "seats.csv": (
        "seats",
        ["screen_id", "seat_id", "row_label", "seat_no", "tier"]
    ),

    "movies.csv": (
        "movies",
        ["movie_id", "title", "certificate", "release_date"]
    ),

    "shows.csv": (
        "shows",
        [
            "show_id",
            "screen_id",
            "movie_id",
            "start_ts",
            "base_price_recliner",
            "base_price_prime",
            "base_price_classic"
        ]
    ),

    "users.csv": (
        "users",
        ["user_id", "user_name", "mobile", "loyalty_points"]
    ),

    "presold_seats.csv": (
        "presold_seats",
        ["show_id", "seat_id", "booking_ref"]
    )
}


# ==================================================
# VALUE CONVERSION
# ==================================================

INTEGER_COLUMNS = {
    "total_seats",
    "seat_no",
    "loyalty_points"
}

DECIMAL_COLUMNS = {
    "base_price_recliner",
    "base_price_prime",
    "base_price_classic"
}


def convert_value(column, value):

    if column in INTEGER_COLUMNS:
        return int(value)

    if column in DECIMAL_COLUMNS:
        return float(value)

    return value


# ==================================================
# CSV IMPORT FUNCTION
# ==================================================

def import_csv(connection, filename, table_name, columns):

    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Missing dataset file: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        actual_columns = reader.fieldnames

        if actual_columns != columns:
            raise ValueError(
                f"Column mismatch in {filename}.\n"
                f"Expected: {columns}\n"
                f"Found: {actual_columns}"
            )

        placeholders = ",".join("?" for _ in columns)

        column_names = ",".join(columns)

        query = (
            f"INSERT INTO {table_name} "
            f"({column_names}) "
            f"VALUES ({placeholders})"
        )

        count = 0

        for row in reader:

            values = [
                convert_value(column, row[column])
                for column in columns
            ]

            connection.execute(query, values)

            count += 1

    print(f"Imported {count} records into {table_name}")

    return count


# ==================================================
# VALIDATE PRESOLD SEATS
# ==================================================

def validate_presold_seats(connection):

    invalid = connection.execute(
        """
        SELECT p.show_id, p.seat_id
        FROM presold_seats p

        JOIN shows sh
            ON sh.show_id = p.show_id

        LEFT JOIN seats s
            ON s.screen_id = sh.screen_id
            AND s.seat_id = p.seat_id

        WHERE s.seat_id IS NULL
        """
    ).fetchall()

    if invalid:
        raise ValueError(
            f"Invalid presold seat references: {invalid[:10]}"
        )

    print("Presold seat validation successful.")


# ==================================================
# VERIFY DATABASE COUNTS
# ==================================================

def verify_database(connection):

    expected = {
        "venues": 2,
        "screens": 6,
        "seats": 456,
        "movies": 4,
        "shows": 12,
        "users": 25,
        "presold_seats": 422
    }

    print("\nDATABASE VERIFICATION")
    print("-" * 40)

    for table, expected_count in expected.items():

        actual_count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(
            f"{table}: {actual_count} "
            f"(Expected: {expected_count})"
        )

        if actual_count != expected_count:
            raise ValueError(
                f"Record count mismatch in {table}"
            )

    print("-" * 40)
    print("All record counts verified successfully.")


# ==================================================
# MAIN IMPORT PROCESS
# ==================================================

def main():

    print("\n======================================")
    print(" T042 OFFICIAL DATASET IMPORT")
    print("======================================")

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Dataset folder not found: {DATA_DIR}"
        )

    if DB_PATH.exists():
        existing = sqlite3.connect(DB_PATH)

        try:
            tables = existing.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()

            if tables:
                raise RuntimeError(
                    "Official database already contains tables. "
                    "Import stopped to prevent duplicate records. "
                    "Do not delete it; inspect it before retrying."
                )

        finally:
            existing.close()

    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    try:

        connection.executescript(SCHEMA)

        # Import parent tables first.
        for filename in [
            "venues.csv",
            "screens.csv",
            "seats.csv",
            "movies.csv",
            "shows.csv",
            "users.csv",
            "presold_seats.csv"
        ]:

            table_name, columns = CSV_CONFIG[filename]

            import_csv(
                connection,
                filename,
                table_name,
                columns
            )

        validate_presold_seats(connection)

        verify_database(connection)

        connection.commit()

        print("\n======================================")
        print(" DATASET IMPORT SUCCESSFUL")
        print("======================================")

        print(f"\nDatabase location:\n{DB_PATH}")

    except Exception:

        connection.rollback()

        print("\nIMPORT FAILED. Database transaction rolled back.")

        raise

    finally:

        connection.close()


if __name__ == "__main__":
    main()