# Step 7 — OSM Routing (arbitrary routes)

## What was built

`backend/geo.py` — replaces the 11 baked-in presets so any Mumbai route works,
using only free OpenStreetMap services (no Google, no billing account, no key):
- `geocode(query)` — Photon, biased to Mumbai + filtered to a regional bbox.
- `route_distance(o, d)` — OSRM road distance, with a haversine fallback.
- `in_no_auto_zone(lat, lon)` — point-in-polygon against an approximate
  South-Mumbai / Island-City polygon.

## Why this shape (product + eng decisions)

1. **OSM over Google (confirmed with user).** Google Maps would cost ~$0 at
   demo scale but requires a billing account with a card on file and a key
   that would sit on a public site — real friction and a standing liability
   for a portfolio piece. Photon + OSRM are genuinely free and keyless.
2. **The no-auto zone became a polygon.** In v1 it was a boolean baked into
   each preset route. With arbitrary geocoded points that no longer works, so
   it's now a ray-casting point-in-polygon test against an approximate polygon
   of the area south of the Mahim/Bandra(W)–Sion line. Flagged as approximate.

## The bug that shaped the design: local TLS can't reach OSRM

Running `geo.py` locally, Photon and Open-Meteo worked but OSRM failed with
`SSLV3_ALERT_HANDSHAKE_FAILURE`. Diagnosed it: macOS system Python 3.9 ships
LibreSSL 2.8.3 (ancient), which can't negotiate TLS with `router.project-osrm.org`
specifically — while `curl` (system TLS) and the other two HTTPS services work
fine. It's a local-only issue; Render's modern Python/OpenSSL will handshake
fine (curl proves the server supports modern TLS).

**Fix, without hand-waving "works in prod":** `route_distance()` tries OSRM and
falls back to a haversine great-circle distance × 1.3 (a rough road-factor)
when OSRM is unreachable — returning `{km, source}` so the source ("osrm" vs
"haversine_estimate") is visible to the UI. This keeps the backend
self-sufficient and locally testable, degrading to a clearly-labeled estimate
instead of crashing. Same honesty principle as the rest of the product: when
we're estimating, say so.

## Note on architecture (for the frontend step)

Because the browser has modern TLS and both Photon/OSRM are CORS-enabled, the
frontend will call Photon directly for autocomplete (fast, no Render cold-start
latency per keystroke). The backend owns the deterministic parts — zone check,
surge, fare, decision — and will compute distance server-side (real OSRM on
Render, haversine fallback locally).

## Verification

Ran `geo.py`: geocoding returns Mumbai-biased results with coords; zone
spot-checks all correct (Colaba & Fort → in no-auto zone; Andheri & Powai →
not); distance returns a sane 9.07 km for Andheri→BKC via the haversine
fallback locally (real OSRM road distance on Render).
