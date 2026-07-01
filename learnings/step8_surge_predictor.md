# Step 8 — Surge Predictor

## Why this exists (the feedback that prompted it)

v1 had a manual surge slider. Real users (people Nibhrit showed it to) flagged
that making the user pick the surge level makes no sense — it's the one thing
they can't see, which is *why* they're asking. Correct critique.

## What was built

`backend/surge.py` — `predict_surge(hour, weekday, fetch_weather)` returns a
`SurgePrediction`: a multiplier, a plain label ("No / Mild / Moderate / High
surge likely"), the reasons behind it, and a weather note. Signals:
- **Time of day** — rush hours (8–10am, 5–8pm) and late-night scarcity (12–4am)
- **Day of week** — Fri/Sat night demand
- **Live weather** — rain via Open-Meteo (free, keyless); rain is the single
  biggest surge driver in Mumbai, weighted highest

## The load-bearing framing: predicted, never "live"

The critique was "decide surge from real-time data." But true real-time *actual*
surge has no public source — it's the same hard/legally-grey problem scoped out
from day one. So the honest resolution is a predicted *likelihood*, always
labeled as a prediction, never presented as live actual surge. This is
strictly more honest than BOTH the thing it replaces (a manual guess) AND the
thing that was literally asked for (a "real-time" number we can't truthfully
deliver). It's the same principle the whole product runs on: don't claim more
certainty than the data supports.

Kept the manual override (per user decision) for scenario exploration — the
slider had one legitimate use, letting someone *see* the surge-proof-meter
mechanism move, which is worth preserving as an "advanced" control, just not as
the forced default.

## Design details worth noting

- **Fail-soft weather.** If Open-Meteo is unreachable, the prediction silently
  degrades to time-of-day only and says so in the weather note, rather than
  erroring. The backend never hard-depends on an external call succeeding.
- **It's a heuristic, not a trained model.** The weights are hand-set and
  illustrative. Flagged as such — presenting hand-tuned weights as a
  calibrated model would be the same false-confidence failure the product
  exists to avoid. A real version would learn these from historical fare data.

## Verification

Ran `surge.py`: time/day-only scenarios behave sensibly (off-peak 1.0x, rush
1.3x, late-night 1.2x). The live call worked and picked up real conditions —
it was lightly raining in Mumbai at run time (1.1 mm), correctly yielding a
1.3x "mild surge likely" with reason "rain".
