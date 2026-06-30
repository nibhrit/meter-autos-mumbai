# Meter Autos

A Mumbai ride-fare decision tool — should you take a street meter auto, or open Uber/Ola/Rapido?

Portfolio prototype by Nibhrit Mohanty (MBA, IIM Mumbai / former PayPal SDE). Not affiliated with
Uber, Ola, Rapido, or any transport authority. See [CLAUDE.md](CLAUDE.md) for the full spec.

## Why this exists

Mumbai auto-rickshaw fares are government-fixed and published (Maharashtra RTO tariff), but
Uber/Ola/Rapido pricing is proprietary and dynamic. Existing comparison tools give a confident
verdict even when they're estimating app fares they admit could be wrong (surge, etc). This tool
is built to be honest about that: a strong call when the economics are clearly one-sided, and a
plain "toss-up, here's your surge-proof anchor" when they're not.

## Stack

- **Fare engine** (`backend/fare_engine.py`) — deterministic Mumbai RTO meter math + modeled app fares
- **Decision logic** (`backend/decision.py`) — verdict + calibrated confidence + zone/surge handling
- **NL assistant** (`backend/assistant.py`) — Claude front door; never computes a fare, only translates
- **API** (`backend/main.py`) — FastAPI, `/routes`, `/decide`, `/ask`
- **Frontend** — single-page demo (in progress)

## Running locally

```bash
cd backend
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > ../.env
uvicorn main:app --reload
```

## Build log

Step-by-step build notes and product-decision rationale are in [`learnings/`](learnings/).
