"""
FastAPI app. Three endpoints:
  GET  /routes  -> list preset routes (frontend populates its picker)
  POST /decide  -> structured input -> Decision (no LLM, deterministic)
  POST /ask     -> free-text query -> NL assistant pipeline
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from assistant import ask as assistant_ask
from decision import decide, Decision
from fare_engine import TimeOfDay, FareQuote
from routes import list_routes

app = FastAPI(title="Meter Autos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # portfolio demo — not a production CORS policy
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecideRequest(BaseModel):
    route_id: str
    time_of_day: str = "day"  # "day" | "night"
    surge: float = 1.0


class AskRequest(BaseModel):
    query: str


def _quote_to_dict(q: FareQuote) -> dict:
    return {"provider": q.provider, "tier": q.tier, "fare": q.fare, "is_official_tariff": q.is_official_tariff, "note": q.note}


def _decision_to_dict(d: Decision) -> dict:
    return {
        "verdict": d.verdict,
        "confidence": d.confidence,
        "meter_fare": d.meter_fare,
        "app_options": [_quote_to_dict(q) for q in d.app_options],
        "savings": d.savings,
        "reasoning": d.reasoning,
        "surge_proof_note": d.surge_proof_note,
        "zone_flag": d.zone_flag,
        "car_tier_insight": d.car_tier_insight,
    }


@app.get("/routes")
def get_routes():
    return {"routes": list_routes()}


@app.post("/decide")
def post_decide(req: DecideRequest):
    if req.time_of_day not in ("day", "night"):
        raise HTTPException(400, "time_of_day must be 'day' or 'night'")
    try:
        tod = TimeOfDay.NIGHT if req.time_of_day == "night" else TimeOfDay.DAY
        result = decide(req.route_id, tod, req.surge)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _decision_to_dict(result)


@app.post("/ask")
def post_ask(req: AskRequest):
    result = assistant_ask(req.query)
    if not result["matched"]:
        return {"matched": False, "message": result["message"]}
    return {
        "matched": True,
        "route": result["route"],
        "params": result["params"],
        "decision": _decision_to_dict(result["decision"]),
        "reply": result["reply"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
