# Step 10 — NL Tab: Arbitrary Routes

## The gap (caught by the user)

After the routing upgrade, the Route tab handled any Mumbai route but the NL
"Ask" tab still only matched the 11 presets — I'd rebuilt one path and not the
other. The user spotted the inconsistency.

## What changed

`backend/assistant.py` now extracts **free-text pickup and drop** place names
instead of matching a preset `route_id`. The flow:
1. Claude extracts `pickup`, `destination` (as strings), plus time and a surge
   signal inferred from the wording.
2. Deterministic code geocodes both (Photon), computes distance (OSRM), checks
   the zone polygon, and calls the same `decide_core` the Route tab uses.
3. `main.py`'s `/ask` attaches the same distance/surge metadata as
   `/decide_route`, so both tabs render identically.

So "auto from Lokhandwala to Nariman Point at 1am?" now works — neither is a
preset — and correctly flags Nariman Point as no-auto zone.

## The refuse-to-guess guarantee moved down a layer, intact

Before: refuse if not one of 11 preset routes. Now: Claude still only extracts
place *names* (never coordinates, never fares), and a mis-named or non-Mumbai
place returns no geocode hit and is refused — not guessed. Verified: "Delhi to
Mumbai", "Bangalore to Chennai", "my house to the office", and gibberish all
still correctly decline. The LLM's surface area is unchanged: it can mis-name a
place, which fails safe, but it can't invent a location or a price.

## Eval re-baselined (not left reporting a stale 100%)

The old NL eval matched preset IDs, so several "correct refusal" cases only
passed *because* they weren't presets (e.g. "Churchgate to Marine Drive"). Under
the new behavior those are real, geocodable routes. Rewrote `NL_CASES` to the
new reality:
- 12 should-match cases — now including genuinely non-preset routes (Lokhandwala
  →Nariman Point, Colaba→Churchgate, Juhu→Andheri, Powai→Vikhroli, Ghatkopar→
  Chembur) — each checked for the right places resolving AND the correct
  no-auto-zone call.
- 6 should-refuse cases — out-of-region, vague, and gibberish.

A match now counts as correct only if the right places geocoded *and* the zone
flag is right, so the metric actually exercises the new pipeline (including
point-in-polygon zone detection through the NL path), not just "did it match."

## Results (re-run, live Claude + geocoding)

- Decision engine regression: **22/22** (unchanged; `decide_core` refactor safe).
- NL high-confidence precision: **100%** (12/12) — right places + right zone.
- Correct refusal rate: **100%** (6/6).

Same honest caveat as before: 18 cases validates the design, not bulletproof
reliability. Geocoding edge cases (ambiguous names, typos) are the next eval to
add.
