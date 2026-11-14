# Cinema and Event Ticketing System

## Team T042 – PS-040

### BR-01: Seat Hold

* A user can hold a maximum of 10 seats per show.
* A hold remains valid for 8 minutes.
* A second hold by the same user cancels their previous hold.
* Expired seats become available again.

### BR-02: Seat Contiguity

* A hold of 2–4 seats must be in the same row and contiguous.
* The booking must follow the single-gap restriction.

### BR-03: Dynamic Pricing

* Occupancy below 50%: Base price × 1.0.
* Occupancy from 50% to below 80%: Base price × 1.15.
* Occupancy 80% or above: Base price × 1.3.
* The occupancy multiplier is frozen when seats are held.

### BR-04: Time-Based Pricing

* Shows starting within 2 hours: 10% discount on CLASSIC seats.
* Opening-day shows: 20% increase on all tiers.
* Opening-day pricing takes priority over the last-minute discount.

### BR-05: Convenience Fee

* First 2 tickets: ₹30 per ticket.
* Additional tickets: ₹25 per ticket.
* GST on convenience fee: 18%.

### BR-06: Entertainment GST

* Ticket price up to ₹100: 12% GST.
* Ticket price above ₹100: 18% GST.
* GST is calculated after price adjustments and discounts, before fees.

### BR-07: Group Offer

* Bookings of 6 or more seats receive 10% discount.
* Group offer and matinee discount cannot be combined.
* Higher discount wins.

### BR-08: Weekday Matinee

* Shows before 12 PM, Monday to Friday.
* ₹50 discount on CLASSIC and PRIME seats.

### BR-09: Loyalty Points

* Earn 1 point for every ₹10 of final ticket price after discounts and loyalty redemption.
* GST and convenience fees are excluded from points calculation.
* 100 points = ₹50 discount.
* Maximum redemption is 50% of ticket price.
* Cancelled bookings reverse earned points.
### BR-10: Cancellation

* More than 4 hours before show: 75% refund.
* 2–4 hours before show: 50% refund.
* Within 2 hours: No refund.
* Venue cancellation: 100% refund including fees and 2× loyalty credits.

### BR-11: Age Restriction

* A-rated shows require every ticket holder to be at least 18 years old.
* Bookings with underage ticket holders must be rejected.

### BR-12: Seat Tier Downgrade

* If a RECLINER seat is released and re-held within the same minute, the new holder uses the original frozen occupancy for pricing.
