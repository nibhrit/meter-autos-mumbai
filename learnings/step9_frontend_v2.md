# Step 9 — Frontend Rebuild (v2)

## What changed and why

Three pieces of feedback drove this, all acted on after showing design options
(the v1 look-and-feel was chosen solo — a process miss owned and corrected):

1. **11 presets felt like a weak demo.** → Free-text autocomplete for any Mumbai
   pickup/drop, powered by Photon directly from the browser (CORS confirmed in
   practice, not just via curl). Preset "Try" chips kept as quick-demo
   affordances and an offline fallback.
2. **Manual surge slider made no sense to users.** → Surge now auto-predicted
   by the backend (time + day + live weather), shown as a labeled prediction
   ("Mild surge likely · 1.3×") with the reasons and weather note. Manual
   override moved under an "Advanced" disclosure for scenario exploration.
3. **No easy way to reach the demo.** → "Go to demo" CTA in a sticky top bar,
   plus a hero "Try the demo" button.

## The A/B theme toggle (the design decision)

Showed three visual directions as a comparison widget; the user liked two and
asked for a **light/dark toggle, default dark**:
- **Dark = "Street Meter"** — charcoal + black/yellow auto livery, sans. Strong
  Mumbai identity.
- **Light = "Public Utility"** — warm paper, serif headings, civic green.
  Reinforces the honesty thesis (reads like a tool that won't mislead you).

Implemented as one codebase: `html[data-theme]` + CSS variables. Every color,
plus the heading font (`--font-heading`: sans in dark, serif in light), is a
variable, so the toggle just flips `data-theme`. Persisted to localStorage.

## Honesty surfaced in the UI (on-brand)

The new metadata is shown, not hidden: distance value **and its source** ("road
distance" vs "est. distance"), the predicted-surge label with reasons + live
weather note, and — when OSRM is unreachable and the haversine fallback kicks
in — an explicit line that the distance is a straight-line estimate. Same
principle as the whole product: when we're estimating, say so.

## Verification (browser, both themes, both input paths, live prod)

- Dark theme loads by default; toggle flips to the serif/green light theme
  correctly; no console errors in either.
- Example chip → `/decide_route` → HIGH-confidence verdict with distance/surge
  metadata and live-weather surge note.
- Typed autocomplete (Photon browser-direct) → picked "Worli" → verdict
  correctly returns the no-auto-zone flag via the point-in-polygon check on the
  geocoded coordinates (not a preset boolean).
- Switched `API_BASE` to the live Render URL and confirmed prod returns real
  OSRM road distance (`source: osrm`, 11.75 km Andheri→BKC) — the haversine
  fallback is local-only, as designed. Frontend redeploys via GitHub Pages.

## Note on evals

The decision core is unchanged in behavior (the refactor to `decide_core` is
covered by the existing 22/22 regression, re-run and still green). The new
integration layers (geocoding, routing, surge) are verified manually end-to-end
rather than in the automated suite — they depend on live external services,
which don't belong in a deterministic regression eval. Flagged rather than
pretending the automated suite covers them.
