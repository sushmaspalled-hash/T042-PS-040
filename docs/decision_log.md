# Decision Log
## T042-PS-040: Cinema and Event Ticketing with Seat Holds and Dynamic Pricing

This document records the major technical and implementation decisions made during project development.

| ID | Decision | Reason |
|---|---|---|
| D01 | Use Python as the programming language. | Easy implementation and modular development. |
| D02 | Use SQLite as the database. | Lightweight database suitable for this project. |
| D03 | Divide the application into separate modules. | Improves code organization and maintainability. |
| D04 | Implement temporary seat holds. | Prevents multiple users from booking the same seats simultaneously. |
| D05 | Set seat hold duration to 8 minutes. | Follows the assigned business requirements. |
| D06 | Implement contiguous seat validation. | Ensures valid seat selection and prevents isolated seats. |
| D07 | Freeze dynamic pricing at hold time. | Maintains consistent pricing during the booking process. |
| D08 | Implement occupancy-based pricing. | Adjusts ticket prices according to seat occupancy. |
| D09 | Implement cancellation and refund rules. | Ensures refunds follow the specified cancellation policy. |
| D10 | Implement loyalty points. | Supports earning, redemption, and reversal of points. |
| D11 | Use Pytest for testing. | Verifies application functionality and business rules. |
| D12 | Generate CSV reports. | Makes booking information and system results easy to review. |
| D13 | Use Git and GitHub for version control. | Supports collaboration and project tracking. |

## Testing Decision
The project uses automated tests to validate booking, pricing, cancellation, seat management, and edge cases.

Latest recorded test result: 26 tests passed.

## Final Decision
The backend is implemented using Python and SQLite with a modular service architecture. The implementation is validated using automated tests.
