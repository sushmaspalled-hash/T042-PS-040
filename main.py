from services.seat_service import (
    get_available_seats,
    get_all_seats,
    hold_seats,
    release_hold
)

from services.booking_service import confirm_booking
from services.cancellation_service import cancel_booking
def main():
    print("\n================================")
    print(" CINEMA AND EVENT TICKETING")
    print("================================")

    while True:
        print("\n1. View all seats")
        print("2. View available seats")
        print("3. Hold seats")
        print("4. Confirm booking")
        print("5. Release held seats")
        print("6. Cancel booking")
        print("7. Exit")

        choice = input("\nEnter your choice: ")

        try:
            if choice == "1":
                show_id = int(input("Enter show ID: "))
                print(get_all_seats(show_id))

            elif choice == "2":
                show_id = int(input("Enter show ID: "))
                print(get_available_seats(show_id))

            elif choice == "3":
                customer_id = int(input("Customer ID: "))
                show_id = int(input("Show ID: "))
                seat_ids = list(map(
                    int,
                    input("Enter seat IDs separated by commas: ").split(",")
                ))

                print(hold_seats(customer_id, show_id, seat_ids))

            elif choice == "4":
                customer_id = int(input("Customer ID: "))
                show_id = int(input("Show ID: "))
                seat_ids = list(map(
                    int,
                    input("Enter seat IDs separated by commas: ").split(",")
                ))

                print(confirm_booking(customer_id, show_id, seat_ids))

            elif choice == "5":
                customer_id = int(input("Customer ID: "))
                show_id = int(input("Show ID: "))

                print(release_hold(customer_id, show_id))

            elif choice == "6":
                booking_id = int(input("Booking ID: "))
                print(cancel_booking(booking_id))

            elif choice == "7":
                print("Application closed.")
                break

            else:
                print("Invalid choice.")

        except (ValueError, TypeError) as error:
            print("Error:", error)

        except Exception as error:
            print("Unexpected error:", error)


if __name__ == "__main__":
    main()