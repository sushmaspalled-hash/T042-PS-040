from database.db import get_connection


def seed_database():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Stop duplicate insertion
        if cursor.execute("SELECT COUNT(*) FROM venues").fetchone()[0] > 0:
            print("Sample data already exists!")
            return

        # 1. Insert venues
        venues = [
            ("PVR Cinemas", "Bengaluru"),
            ("INOX Cinemas", "Mysuru")
        ]

        cursor.executemany(
            "INSERT INTO venues (venue_name, location) VALUES (?, ?)",
            venues
        )

        # 2. Insert screens (3 per venue)
        screens = []

        for venue_id in range(1, 3):
            for number in range(1, 4):
                screens.append(
                    (venue_id, f"Screen {number}")
                )

        cursor.executemany(
            "INSERT INTO screens (venue_id, screen_name) VALUES (?, ?)",
            screens
        )

        # 3. Insert seats (10 per screen)
        seats = []

        for screen_id in range(1, 7):
            for row in ["A", "B"]:
                for number in range(1, 6):

                    if row == "A" and number <= 3:
                        tier = "RECLINER"
                    elif row == "B" and number >= 4:
                        tier = "CLASSIC"
                    else:
                        tier = "PRIME"

                    seats.append(
                        (screen_id, row, number, tier)
                    )

        cursor.executemany(
            """
            INSERT INTO seats
            (screen_id, row_name, seat_number, tier)
            VALUES (?, ?, ?, ?)
            """,
            seats
        )

        # 4. Insert shows
        shows = [
            (1, "The Grand Adventure", "2026-11-10 10:30:00",
             300, 200, 120, 0, 0, "SCHEDULED"),

            (2, "Mystery Night", "2026-11-11 18:30:00",
             350, 250, 150, 1, 1, "SCHEDULED")
        ]

        cursor.executemany(
            """
            INSERT INTO shows
            (screen_id, movie_name, start_time,
             base_recliner, base_prime, base_classic,
             is_opening_day, is_a_rated, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            shows
        )

        # 5. Insert customers
        customers = [
            ("Customer One", 500),
            ("Customer Two", 200)
        ]

        cursor.executemany(
            """
            INSERT INTO customers (customer_name, loyalty_points)
            VALUES (?, ?)
            """,
            customers
        )

        conn.commit()
        print("Sample data inserted successfully!")

    except Exception as error:
        conn.rollback()
        print("Error inserting sample data:", error)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
    