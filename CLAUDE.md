# Meter Autos — Claude Code Instructions

## What this project is

A portfolio prototype demonstrating an **honest, confidence-aware ride-fare decision tool** for Mumbai
commuters: should you take a street meter auto, or open an app (Uber / Ola / Rapido)?
Built by Nibhrit Mohanty (MBA, IIM Mumbai / former PayPal SDE) as a PM interview portfolio piece.

**The core insight (the reframe):** The auto-vs-app decision only *actually matters* in two situations,
and existing tools (MeterSahi, Ottometer, Comparify) blur them by giving confident verdicts on estimated
fares they admit are wrong during surge:
1. **Short hops (<3 km):** meter auto (₹26–50) vs app *car* min fare (₹60–100+) — a large, real gap.
2. **Surge moments:** the street meter is **government-fixed and surge-proof**; app fares spike 1.5×+.
   This is when knowing the meter number has the most leverage.

So this tool gives a **strong verdict when the economics are clear, and is honest about confidence**
(with the surge-proof meter as the anchor) when they're not. It is *not* a generic comparator.

**What it is NOT:** Not a live integration. App fares are *modeled* from published rate cards, not scraped.
This demonstrates the decision-logic and product judgment that a ride-comparison product would build natively.

---

## Stack — confirmed

| Layer | Choice | Reason |
|-------|--------|--------|
| LLM | Claude API (Haiku default; latest capable model) | Powers the NL assistant front door; cost-efficient |
| Backend | FastAPI (Python) | Lightweight; houses the deterministic fare engine + decision logic |
| Vector DB | N/A | No retrieval needed — fares are computed, not retrieved |
| Frontend | Single HTML file (landing page + embedded demo) | Portfolio-shareable, no framework |
| Deployment | Render (backend) + GitHub Pages (frontend) — when asked | Free tier, live URL |

---

## Folder structure

```
Meter Autos/
├── CLAUDE.md
├── backend/
│   ├── fare_engine.py      # deterministic Mumbai RTO meter math + app-fare models
│   ├── decision.py         # compare → verdict + confidence + savings + zone/surge logic
│   ├── assistant.py        # Claude NL layer: parse query → call engine → plain-language answer
│   ├── routes.py           # curated preset Mumbai routes (baked-in distances)
│   └── main.py             # FastAPI app
├── frontend/               # landing page + embedded demo (single HTML)
├── evals/                  # test set + eval script
├── learnings/              # one stepN_*.md doc per build step
└── README.md
```

---

## Domain facts (source of truth for the engine)

**Mumbai auto-rickshaw RTO tariff (eff. 1 Feb 2025):**
- Minimum fare **₹26** (covers first 1.5 km)
- **₹17.14 per km** beyond 1.5 km
- Night surcharge **+25%** (12 AM–5 AM)
- Waiting ~10% of basic per-km; rounding to nearest rupee
- Formula: `fare = 26 + max(0, dist_km − 1.5) × 17.14`, then night/rounding

**App fare models (modeled, not live):**
- App *autos* (Uber/Ola/Rapido Auto) ≈ RTO meter fare + flat platform fee (₹5–8) — gap vs street is tiny.
- App *cars* (UberGo/Ola Mini) have high min fares (~₹60–100) — this is the real short-trip gap.
- Surge is a scenario multiplier (1.0× / 1.3× / 1.5×+) applied to app fares only; meter is surge-proof.

**Zone rule:** Autos are banned south of Bandra (W) / Sion — all of South Mumbai is auto-free. The tool
must flag when a route enters the no-auto zone and suppress the auto recommendation there.

---

## API contract — do not change without flagging

`POST /decide`
- **In:** `{ "route_id": str, "time_of_day": "day"|"night", "surge": float }`
  (or `{ "query": str }` for the NL endpoint `POST /ask`)
- **Out:** `{ verdict, confidence: "high"|"medium"|"low", meter_fare, app_options: [...],
  savings, reasoning, surge_proof_note, zone_flag }`
- `verdict`, `confidence`, and `meter_fare` must always be present.

---

## Scope — v1

**In scope:**
- Deterministic Mumbai meter fare engine (RTO tariff above).
- Modeled app fares: Uber/Ola/Rapido — both auto and car tiers — from published rate cards + min fares.
- Decision engine: verdict + **calibrated confidence** + savings; surge-proof anchor logic; zone flagging.
- NL assistant layer (Claude): "should I take an auto to Andheri at 6pm?" → verdict in plain language.
- Curated preset Mumbai routes (real origin→dest pairs with baked-in distances) + manual distance fallback.
- Single-page frontend: problem hero → how it works → stack cards → live demo → evals.
- Disclaimer strip on the frontend.

**Explicitly out of scope for v1:**
- Live app-fare scraping or official APIs (modeled instead — flagged as the real hard problem).
- Live maps / geocoding (curated presets instead).
- In-app booking / deep links (may show, not core).
- Real-time surge feeds (surge is a user-selectable scenario).
- Cities other than Mumbai; auth; accounts; persistence.

---

## Eval standard

- ~20–30 test cases across: short hops, long trips, day vs night, surge on/off, no-auto-zone routes.
- **Primary metric: high-confidence recommendation precision** — when the tool gives a HIGH-confidence
  verdict, how often is it actually correct. Chosen because the failure mode that destroys trust is
  *false confidence* (telling someone to skip the auto when it was cheaper), analogous to false-positive
  rate in fraud — better to say "uncertain, here's your anchor" than to confidently mislead.
- Secondary: **coverage** (% of trips we can give a confident verdict on) and savings accuracy.

---

## Working style — follow in every session

1. **One layer at a time.** Build and verify each component before the next.
   Order: fare engine → decision logic → NL assistant → frontend → evals.
2. **Explain after every component.** What it does and why — the user owns every layer for interviews.
3. **Flag product decisions explicitly.** Name the decision and the reasoning.
4. **Features discussion before code.** Confirm new features before implementing.
5. **Verify locally before declaring done.** Run it, observe real output.
6. **Write a learnings doc after every step** in `learnings/` (`stepN_short_name.md`): what was built,
   what each file does, key concepts in plain English, product decisions. Permanent requirement.

---

## Conventions

- Commit messages: short and to the point. No co-author / generated-with trailers.
- Never hardcode secrets — env vars only (`ANTHROPIC_API_KEY`); gitignore `.env` and `.claude/`.
- Disclaimer strip on every frontend: "Work sample built by Nibhrit Mohanty — Not affiliated with Uber,
  Ola, Rapido, or any transport authority. App fares are modeled estimates."
- Branch/commit/push only when asked.
