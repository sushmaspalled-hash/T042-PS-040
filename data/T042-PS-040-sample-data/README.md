# PS-040 – Cinema and Event Ticketing with Seat Holds and Dynamic Pricing — Sample Data Pack

Prepared by 10 SECONDS for Team T042.

## Files

| File | What it holds | Row count |
|---|---|---|
| `venues.csv` | 2 venues | 2 data rows |
| `screens.csv` | 3 screens per venue | 6 data rows |
| `seats.csv` | Seat map per screen (rows A-E CLASSIC, F-G PRIME, H RECLINER) | 456 data rows |
| `movies.csv` | Movies with certificate and release date (opening day = release date) | 4 data rows |
| `shows.csv` | 12 shows Fri–Sun with base price per tier | 12 data rows |
| `users.csv` | Customers with loyalty point balances | 25 data rows |
| `presold_seats.csv` | Seats already sold for each show before this command stream | 422 data rows |
| `commands.txt` | 90 commands: 50 HOLD (15 expire, 3 rejected), 30 BOOK, 8 CANCEL, 1 RELEASE, 1 CANCEL_SHOW, plus print requests | 132 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and only appears in columns whose notes say so.

### `venues.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| venue_id | string | VEN-nn | — | — |
| venue_name | string | — | — | fictional |
| city | string | — | — | — |

### `screens.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| screen_id | string | SCR-nn | — | — |
| venue_id | string | — | venues.csv | — |
| screen_name | string | — | — | — |
| total_seats | int | — | — | occupancy denominator |

### `seats.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| screen_id | string | — | screens.csv | — |
| seat_id | string | ROWn | — | unique within a screen |
| row_label | string | A-H | — | — |
| seat_no | int | — | — | 1 and the last number are row edges |
| tier | enum | — | CLASSIC, PRIME, RECLINER | — |

### `movies.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| movie_id | string | MOV-nn | — | — |
| title | string | — | — | fictional |
| certificate | enum | — | U, UA, A | A = all holders 18+ |
| release_date | date | — | — | — |

### `shows.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| show_id | string | SH-nn | — | — |
| screen_id | string | — | screens.csv | — |
| movie_id | string | — | movies.csv | — |
| start_ts | timestamp | — | — | — |
| base_price_recliner | decimal | Rs | — | — |
| base_price_prime | decimal | Rs | — | — |
| base_price_classic | decimal | Rs | — | — |

### `users.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| user_id | string | USR-nnn | — | — |
| user_name | string | — | — | — |
| mobile | string | 10 digits | — | — |
| loyalty_points | int | points | — | balance before the stream |

### `presold_seats.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| show_id | string | — | shows.csv | — |
| seat_id | string | — | seats.csv | — |
| booking_ref | string | PRE-... | — | count toward occupancy |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two adjacent `|`) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `HOLD` | `hold_id|ts|user_id|show_id|seats` | Hold seats for 8 minutes (occupancy frozen for this hold) |
| `RELEASE` | `hold_id|ts` | User abandons the hold |
| `BOOK` | `booking_id|ts|hold_id|payment_mode|points_to_redeem|holder_ages` | Pay for a live hold; holder_ages required for A-rated shows (empty otherwise) |
| `CANCEL` | `booking_id|ts` | Customer cancels a booking |
| `CANCEL_SHOW` | `show_id|ts` | Venue cancels the show |
| `PRINT_INVOICE` | `booking_id` | Print the per-ticket price breakup |
| `PRINT_SEATMAP` | `show_id` | Print the seat states for the show |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Hold of 3 seats leaving exactly one empty seat at the row edge**
  - SH-07 row A: hold A2-A4 would leave A1 alone at the row edge -> rejected; the user retries with A1-A3 -> accepted — commands.txt line 27 (`HOLD|HLD-016|2026-10-16 09:40:00|USR-023|SH-07|A2,A3,A4`); commands.txt line 29 (`HOLD|HLD-018|2026-10-16 09:41:30|USR-001|SH-07|A1,A2,A3`); commands.txt line 30 (`BOOK|BKG-008|2026-10-16 09:44:50|HLD-018|CARD|0|`); commands.txt line 31 (`CANCEL|BKG-008|2026-10-16 10:11:00`)
- **EC-02 Occupancy exactly 50% at hold time**
  - SH-04 has 38 of 76 seats presold when this hold is placed -> occupancy exactly 50% -> x1.15 tier — presold_seats.csv rows 87–124 (38 seats for SH-04); commands.txt line 49 (`HOLD|HLD-029|2026-10-16 20:10:00|USR-008|SH-04|E3,E4`); commands.txt line 50 (`BOOK|BKG-015|2026-10-16 20:12:30|HLD-029|UPI|0|`)
- **EC-03 Ticket price exactly Rs 100 after dynamic pricing**
  - SH-03 CLASSIC base 100.00 at multiplier 1.0 -> ticket price exactly Rs 100 -> 12% slab (18% only above Rs 100); A-rated show, both holders adults — commands.txt line 17 (`HOLD|HLD-009|2026-10-15 19:00:00|USR-004|SH-03|B5,B6`); commands.txt line 18 (`BOOK|BKG-006|2026-10-15 19:03:20|HLD-009|CARD|0|24,31`)
- **EC-04 Opening-day show starting in 90 minutes (both adjustments eligible)**
  - Hold at 12:30:00 for the 14:00 opening-day show -> both 'within 2 h' (CLASSIC -10%) and opening day (+20%) qualify; opening-day wins — commands.txt line 35 (`HOLD|HLD-020|2026-10-16 12:30:00|USR-005|SH-02|C4,C5,C6`); commands.txt line 36 (`BOOK|BKG-010|2026-10-16 12:34:00|HLD-020|WALLET|0|`)
- **EC-05 Booking of exactly 6 seats on a weekday matinee**
  - 6 PRIME seats on the Friday 11:00 matinee -> group 10% (24.00 on 240.00) vs matinee Rs 50 off -> the higher discount wins, never both — commands.txt line 15 (`HOLD|HLD-008|2026-10-15 18:45:00|USR-003|SH-01|F3,F4,F5,F6,F7,F8`); commands.txt line 16 (`BOOK|BKG-005|2026-10-15 18:50:00|HLD-008|CARD|0|`)
- **EC-06 Loyalty redemption hitting the 50% cap**
  - User with 2000 points redeems 1500 (= Rs 750) on two CLASSIC tickets -> capped at 50% of ticket price — users.csv row 12 (USR-012); commands.txt line 64 (`HOLD|HLD-035|2026-10-17 09:00:00|USR-012|SH-09|A5,A6`); commands.txt line 65 (`BOOK|BKG-021|2026-10-17 09:02:00|HLD-035|UPI|1500|`)
- **EC-07 Cancellation at exactly 4 hours before show**
  - Booking for SH-06 (21:00) cancelled at 17:00:00 = exactly 4 h before -> boundary between the 75% and 50% refund tiers — commands.txt line 58 (`HOLD|HLD-032|2026-10-17 08:15:00|USR-025|SH-06|G4,G5`); commands.txt line 59 (`BOOK|BKG-018|2026-10-17 08:18:00|HLD-032|CARD|0|29,27`); commands.txt line 87 (`CANCEL|BKG-018|2026-10-17 17:00:00`)
- **EC-08 Second hold by same user while first hold has 10 seconds left**
  - User holds 3 CLASSIC seats at 11:00:00 and places a second hold on SH-05 at 11:07:50 (first hold has 10 s left) -> the first hold is cancelled immediately, not at expiry — commands.txt line 74 (`HOLD|HLD-040|2026-10-17 11:00:00|USR-002|SH-05|D2,D3,D4`); commands.txt line 75 (`HOLD|HLD-041|2026-10-17 11:07:50|USR-002|SH-05|F4,F5,F6`); commands.txt line 76 (`BOOK|BKG-025|2026-10-17 11:08:50|HLD-041|WALLET|0|`); commands.txt line 77 (`CANCEL|BKG-025|2026-10-17 12:00:00`)
- **Extra traps (not in the brief, but realistic):**
  - A-rated SH-06 booking with a 16-year-old holder -> whole booking rejected — commands.txt line 85 (`HOLD|HLD-045|2026-10-17 16:05:00|USR-004|SH-06|C1,C2,C3`); commands.txt line 86 (`BOOK|BKG-027|2026-10-17 16:08:20|HLD-045|CARD|0|34,16,38`)
  - Hold for 12 seats (> 10 per user per show) -> rejected — commands.txt line 78 (`HOLD|HLD-042|2026-10-17 12:00:00|USR-004|SH-11|B1,B2,B3,B4,B5,B6,C1,C2,C3,C4,C5,C6`)
  - 3-seat hold E1, E2, E4 is not contiguous -> rejected — commands.txt line 83 (`HOLD|HLD-044|2026-10-17 14:00:00|USR-015|SH-12|E1,E2,E4`)
  - RECLINER H2-H3 released at 10:23:05 and re-held by another user at 10:23:40 (same minute) -> the new hold reuses the first hold's frozen occupancy — commands.txt line 68 (`HOLD|HLD-037|2026-10-17 10:20:10|USR-008|SH-11|H2,H3`); commands.txt line 70 (`RELEASE|HLD-037|2026-10-17 10:23:05`); commands.txt line 71 (`HOLD|HLD-039|2026-10-17 10:23:40|USR-015|SH-11|H2,H3`); commands.txt line 72 (`BOOK|BKG-024|2026-10-17 10:25:10|HLD-039|CARD|0|`); commands.txt line 84 (`CANCEL|BKG-024|2026-10-17 16:00:00`)
  - BOOK sent 10 min after the hold (> 8 min) -> hold already expired, booking rejected — commands.txt line 94 (`HOLD|HLD-049|2026-10-18 18:00:00|USR-024|SH-12|D7,D8`); commands.txt line 96 (`BOOK|BKG-030|2026-10-18 18:10:00|HLD-049|WALLET|0|30,30`)
  - Second user tries to hold seats that are inside another user's live hold -> rejected (held seats are unavailable to others) — commands.txt line 94 (`HOLD|HLD-049|2026-10-18 18:00:00|USR-024|SH-12|D7,D8`); commands.txt line 96 (`BOOK|BKG-030|2026-10-18 18:10:00|HLD-049|WALLET|0|30,30`); commands.txt line 95 (`HOLD|HLD-050|2026-10-18 18:00:30|USR-004|SH-12|D7,D8`)
  - Venue cancels SH-10 at 2026-10-17 12:00:00 -> every SH-10 booking (e.g. this one, which also redeemed 100 points) refunded 100% incl. fees and credited 2x points — commands.txt line 79 (`CANCEL_SHOW|SH-10|2026-10-17 12:00:00`); commands.txt line 48 (`BOOK|BKG-014|2026-10-16 20:02:30|HLD-028|WALLET|100|`)

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `ticket_lines.csv`

One row per ticket per PRINT_INVOICE.

Columns, in order: `booking_id`, `show_id`, `seat_id`, `tier`, `base_price`, `occupancy_pct_frozen`, `dynamic_multiplier`, `time_adjustment`, `offer_applied`, `offer_discount`, `loyalty_discount`, `ticket_price`, `gst_rate`, `gst_on_ticket`, `convenience_fee`, `gst_on_fee`, `ticket_total`

### `booking_events.csv`

One row per HOLD / RELEASE / BOOK / CANCEL / CANCEL_SHOW outcome (expiries as EXPIRED rows at hold ts + 8 min).

Columns, in order: `ts`, `command`, `reference`, `result`, `reason`, `refund_amount`, `points_earned`, `points_reversed`, `points_credited`

### `seat_maps.csv`

One row per seat per PRINT_SEATMAP.

Columns, in order: `show_id`, `seat_id`, `state`, `reference`

Binding choices: `occupancy_pct_frozen` has 2 decimals and counts presold + booked + held seats (excluding the new hold) at hold time; `state` is FREE, HELD, BOOKED or PRESOLD; `result` is OK, REJECTED or EXPIRED; `offer_applied` is GROUP, MATINEE or NONE; `time_adjustment` is OPENING_DAY, LAST_2H or NONE.
