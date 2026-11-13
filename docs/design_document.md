# Design Document
## T042-PS-040: Cinema and Event Ticketing with Seat Holds and Dynamic Pricing

### 1. Project Overview
The Cinema and Event Ticketing System is a Python-based application designed to manage cinema shows, seat availability, temporary seat reservations, ticket bookings, dynamic pricing, cancellations, refunds, and loyalty points.

### 2. Objectives
- Manage cinema venues, screens, shows, and seats.
- Allow users to temporarily hold available seats.
- Prevent double booking.
- Apply dynamic pricing based on occupancy.
- Calculate ticket prices, GST, and convenience fees.
- Support booking cancellation and refund calculations.
- Maintain customer loyalty points.
- Generate booking, ticket, and seat-map reports.

### 3. Technologies Used
- Programming Language: Python
- Database: SQLite
- Testing: Pytest
- IDE: Visual Studio Code
- Version Control: Git and GitHub

### 4. System Architecture
The application follows a modular architecture.

- Main Application: Provides the application entry point and menu.
- Command Processor: Processes booking commands and business scenarios.
- Database Layer: Manages database connections and SQL operations.
- Services Layer: Handles booking, seat management, pricing, cancellation, loyalty, and reports.
- Models: Contains application data structures.
- Tests: Validates system functionality and business rules.
- Output: Stores generated CSV reports.

### 5. Main Modules

#### 5.1 Seat Management
Manages seat availability, temporary holds, booking status, and seat release.

#### 5.2 Booking Management
Processes seat holds and booking confirmation while preventing duplicate bookings.

#### 5.3 Dynamic Pricing
Calculates ticket prices using occupancy-based multipliers and applicable offers.

#### 5.4 Cancellation and Refund
Processes cancellations and calculates refunds according to the cancellation policy.

#### 5.5 Loyalty Management
Manages loyalty point earning, redemption, reversal, and credits.

#### 5.6 Reporting
Generates ticket details, booking events, and seat-map reports in CSV format.

### 6. Database Design
The system uses SQLite.

Official data includes:
- Venues
- Screens
- Seats
- Movies
- Shows
- Users
- Presold seats

Runtime data includes:
- seat_holds
- bookings
- booking_tickets
- booking_events

### 7. System Workflow
1. Load cinema and show information.
2. Read booking commands.
3. Validate users and seat availability.
4. Apply seat-hold rules.
5. Calculate applicable ticket prices.
6. Confirm valid bookings.
7. Process cancellations and refunds.
8. Update loyalty points.
9. Generate output reports.

### 8. Validation and Testing
The project uses Pytest to validate booking, pricing, cancellation, seat management, and edge cases.

Latest recorded test result: 26 tests passed.

### 9. Expected Outputs
- ticket_lines.csv
- booking_events.csv
- seat_maps.csv

### 10. Conclusion
The system provides a modular backend solution for cinema ticket booking, temporary seat holds, dynamic pricing, cancellation management, loyalty points, and reporting.
