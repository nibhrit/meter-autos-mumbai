# Step 1 — Fare Engine

## What was built

`backend/fare_engine.py` — the deterministic math layer. Given a distance (km),
time of day, and a surge multiplier, it returns:
- **The official street meter fare** (exact, government-published, surge-proof)
- **Five modeled app fares**: Uber Auto, Ola Auto, Rapido Auto (app-booked autos)
  and Uber Go, Ola Mini (app-booked cars)

## What each piece does

- `meter_fare()` — implements the actual Maharashtra RTO tariff (eff. 1 Feb 2025):
  ₹26 minimum for the first 1.5 km, then ₹17.14/km, +25% between 12 AM–5 AM,
  rounded to the nearest rupee. This is the only number in the whole system
  that is *exact*, not estimated.
- `app_auto_fares()` — models app-booked autos as the same RTO meter plus a
  flat platform fee (₹5–8). This deliberately produces a *small* gap vs the
  street meter, because that's what's actually true (verified against the
  real MeterSahi screenshot we reviewed: ₹366 meter vs ₹371–374 app autos).
- `app_car_fares()` — models app car tiers (UberGo, Ola Mini) with their own
  base fare + per-km + per-minute structure, floored at a minimum fare
  (~₹75–79). Trip minutes are estimated from distance at an assumed average
  city speed (18 km/h), since we don't have live traffic data.
- `all_fares()` — single entry point the rest of the app calls.

## Key concept: the asymmetry between "exact" and "modeled"

This is the central product idea, encoded directly in the data structure:
every `FareQuote` carries an `is_official_tariff` flag. The street meter is
the only one that's ever `True`. Uber/Ola/Rapido don't publish rate cards —
their pricing is proprietary and dynamic — so app fares can only ever be
*estimates* calibrated to commonly observed real-world fares. The product's
job (in `decision.py`, next) is to never pretend an estimate is a fact.

## Product decisions made

1. **App fares are modeled, not scraped/live.** Flagged in scope from the
   start (no public API exists, and scraping ride-hailing apps is legally
   grey). The model is calibrated to be directionally realistic, not
   penny-accurate — the UI will need to say so explicitly.
2. **Surge is a user-selectable scenario, not a live feed.** Keeps the demo
   reliable and deterministic while still letting us show the "surge-proof
   meter" insight that's central to the pitch.
3. **Car night surcharge is a soft 10% modeled assumption**, distinct from
   the auto's hard, published 25% RTO surcharge — because there's no
   official published night rate for app cars. Naming this explicitly so
   it doesn't get mistaken for a real tariff in an interview.

## Verification

Ran the engine across 6 scenarios (2/8/15 km × day/night/surge). Confirmed:
- Short hop (2 km): meter ₹35 vs app cars ₹83–86 — the large gap the
  "skip the cab on short trips" thesis depends on.
- Long trip (15 km): meter ₹257 vs app cars ₹310–320 — gap narrows
  proportionally, i.e. the decision gets genuinely closer, which is the
  right behavior for a confidence-aware tool (more on this in step 2).
- App-auto vs meter: consistently ₹5–8 apart at any distance — matches
  the real-world MeterSahi reference data point.
