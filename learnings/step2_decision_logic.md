# Step 2 — Decision Logic + Preset Routes

## What was built

- `backend/routes.py` — 11 curated Mumbai routes (real origin/destination pairs,
  baked-in distances) standing in for live geocoding, per v1 scope. Includes
  short hops, a long trip, and three routes that cross into the no-auto zone
  (Worli, Colaba, Fort).
- `backend/decision.py` — takes a route + time-of-day + surge scenario, calls
  the fare engine, and returns a `Decision`: verdict, confidence, savings,
  reasoning, a surge-proof note, a zone flag, and a car-tier insight.

## How confidence is calibrated

Confidence is based on the **percentage gap** between the meter fare and the
cheapest available app option, not the rupee amount:
- ≥25% apart → **high** confidence, clear winner
- 10–25% apart → **medium**
- <10% apart → **low** — the tool says "toss-up," not a side

This was a deliberate choice (confirmed with the user) over distance-band or
surge-hybrid alternatives: it lets the *data* decide when the tool should
sound confident, rather than hardcoding it to specific trip lengths.

## Key concept: confidence and verdict direction must never disagree

First pass had a bug: at a 9% gap (just under the "medium" cutoff), the tool
said "Take the meter auto" *and* rated itself "low confidence" — a directive
wrapped in a hedge. Fixed by making the verdict's threshold the same as the
confidence threshold: below `MEDIUM_CONFIDENCE_GAP` (10%), the tool says
"toss-up" instead of picking a side. This is the literal mechanism behind the
project's whole thesis — a tool that sounds sure exactly as often as it
actually is sure.

## Key concept: the surge-proof insight requires zero special-casing

Surge is just a multiplier on app fares in `fare_engine.py`; the meter never
moves. Because confidence is gap-based, raising surge to 1.5x mechanically
widens the gap and flips confidence from low → high in the test run below —
the "the meter is your surge-proof anchor" pitch falls directly out of the
math, not a hardcoded rule.

## Product decision: the "car tier trap" call-out

Found mid-build: the *primary* verdict compares the meter to the cheapest
**available** app option — which is almost always an app-auto (Uber/Ola/Rapido
Auto), since those ride on the meter + a small fee. That's the more honest
comparison, but it quietly buries the original pitch ("short hops: people
default to booking a car, and that's where the real gap is").

Resolved by adding `car_tier_insight` as a **secondary** field, not by
changing the primary verdict: when the cheapest *car* tier specifically is
≥20% above the meter, a separate note fires ("if you were about to book a
car instead..."). This keeps the primary verdict honest while still
delivering the original insight where it's true. Flagged explicitly rather
than silently patched, since it changes how the pitch is framed.

## Product decision: zone-restricted routes skip the verdict entirely

When a route enters the no-auto zone (south of Bandra (W)/Sion), there's no
auto-vs-app race to call — auto isn't a legal option. Confidence is set to
`"n/a"` rather than computed, and the verdict becomes "auto not available,
book X" with a `zone_flag`. Treating this as a separate code path (not a
confidence=0 case) avoids a tool that *looks* like it ran the math when it
actually couldn't.

## Verification

Ran 6 scenarios (short/long/night/surge/zone-restricted × 2). Confirmed:
- Andheri→Versova (2.6km equiv) at no surge: toss-up, low confidence — but
  the car-tier insight still correctly fires (Ola Mini ₹104 vs meter ₹55).
- Same route at 1.5x surge: flips to high-confidence "take the auto," with
  the surge-proof note explaining why.
- Worli/Fort routes: correctly short-circuit to "auto not available" with
  zone_flag set and no confidence claimed.
