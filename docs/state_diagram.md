# State Diagram
## T042-PS-040: Cinema and Event Ticketing

### Seat State Transitions

``mermaid
stateDiagram-v2
    [*] --> FREE
    FREE --> HELD: User holds seat
    HELD --> BOOKED: Booking confirmed
    HELD --> FREE: Hold released
    HELD --> FREE: Hold expires after 8 minutes
    BOOKED --> FREE: Booking cancelled and seat released
    FREE --> [*]
`` 

### State Descriptions
- FREE: Seat is available for booking.
- HELD: Seat is temporarily reserved for a user.
- BOOKED: Booking is confirmed.
- EXPIRED: Temporary hold has expired; seat returns to FREE.
- RELEASED: Seat hold has been manually released.

### Conclusion
The state diagram represents the seat reservation lifecycle in the ticketing system.
