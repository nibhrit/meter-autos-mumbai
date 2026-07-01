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

from datetime import datetime, timezone, timedelta

from assistant import ask as assistant_ask
from decision import decide, decide_core, Decision
from fare_engine import TimeOfDay, FareQuote
from routes import list_routes
import geo
from surge import predict_surge

IST = timezone(timedelta(hours=5, minutes=30))

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


class Point(BaseModel):
    label: str
    lat: float
    lon: float


class DecideRouteRequest(BaseModel):
    origin: Point
    dest: Point
    time_of_day: Optional[str] = None      # None -> derive from current IST hour
    surge_override: Optional[float] = None  # None -> predict surge


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


@app.get("/geocode")
def get_geocode(q: str, limit: int = 5):
    """Autocomplete/geocode proxy (frontend may also call Photon directly)."""
    if not q or len(q.strip()) < 2:
        return {"results": []}
    try:
        places = geo.geocode(q.strip(), limit=limit)
    except Exception:
        return {"results": [], "error": "geocoder_unavailable"}
    return {"results": [{"label": p.label, "name": p.name, "lat": p.lat, "lon": p.lon} for p in places]}


@app.post("/decide_route")
def post_decide_route(req: DecideRouteRequest):
    dist = geo.route_distance(req.origin.lat, req.origin.lon, req.dest.lat, req.dest.lon)
    distance_km = dist["km"]

    origin_in_zone = geo.in_no_auto_zone(req.origin.lat, req.origin.lon)
    dest_in_zone = geo.in_no_auto_zone(req.dest.lat, req.dest.lon)
    zone_restricted = origin_in_zone or dest_in_zone
    zone_place = req.dest.label if dest_in_zone else (req.origin.label if origin_in_zone else req.dest.label)

    now = datetime.now(IST)
    if req.time_of_day in ("day", "night"):
        tod = TimeOfDay.NIGHT if req.time_of_day == "night" else TimeOfDay.DAY
    else:
        tod = TimeOfDay.NIGHT if now.hour in (0, 1, 2, 3, 4) else TimeOfDay.DAY

    if req.surge_override is not None:
        surge = round(float(req.surge_override), 2)
        surge_info = {"multiplier": surge, "label": "Manual override",
                      "reasons": ["you set this manually"], "weather_note": "",
                      "is_prediction": False, "overridden": True}
    else:
        pred = predict_surge(hour=now.hour, weekday=now.weekday())
        surge = pred.multiplier
        surge_info = {"multiplier": pred.multiplier, "label": pred.label,
                      "reasons": pred.reasons, "weather_note": pred.weather_note,
                      "is_prediction": True, "overridden": False}

    decision = decide_core(distance_km, zone_restricted, zone_place, tod, surge)
    out = _decision_to_dict(decision)
    out["distance_km"] = distance_km
    out["distance_source"] = dist["source"]
    out["origin_label"] = req.origin.label
    out["dest_label"] = req.dest.label
    out["time_of_day"] = tod.value
    out["surge"] = surge_info
    return out


@app.get("/health")
def health():
    return {"status": "ok"}
