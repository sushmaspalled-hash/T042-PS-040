# Class Diagram
## T042-PS-040: Cinema and Event Ticketing

### Main Class: CommandProcessor
File: services/command_processor.py

Responsibilities:
- Process booking commands
- Manage seat holds and releases
- Validate seat selections
- Calculate occupancy and ticket prices
- Confirm bookings and process cancellations
- Generate invoices and seat maps

### Booking Service
File: services/booking_service.py
- confirm_booking()

### Cancellation Service
File: services/cancellation_service.py
- calculate_refund()
- cancel_booking()
- cancel_show_by_venue()

### Pricing Service
File: services/pricing_service.py
- calculate_dynamic_multiplier()
- calculate_ticket_price()
- calculate_convenience_fee()
- calculate_booking_price()

### Loyalty Service
File: services/loyalty_service.py
- calculate_points()
- calculate_redemption()
- add_loyalty_points()
- redeem_loyalty_points()
- reverse_loyalty_points()

### Seat Service
File: services/seat_service.py
- get_all_seats()
- get_available_seats()
- calculate_occupancy()
- validate_seat_selection()
- hold_seats()
- release_hold()
- release_expired_holds()

### Report Service
File: services/report_service.py

### Architecture
CommandProcessor -> Booking Service
CommandProcessor -> Cancellation Service
CommandProcessor -> Pricing Service
CommandProcessor -> Loyalty Service
CommandProcessor -> Seat Service
CommandProcessor -> Report Service
CommandProcessor -> SQLite Database

### Conclusion
The project follows a modular backend architecture. CommandProcessor coordinates the application workflow, while separate service modules handle booking, cancellation, pricing, loyalty, seat operations, and reporting.
