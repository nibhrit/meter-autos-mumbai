"""
NL assistant layer. Claude does exactly two jobs here, and never a third:

  1. Parse a messy human query ("should I auto from Lokhandwala to Nariman
     Point at 9pm?") into structured inputs: a free-text pickup and drop, plus
     time-of-day and a surge signal inferred from the wording.
  2. Turn the engine's Decision back into a plain-language reply.

Claude never computes a fare, and never resolves a place to coordinates — it
only extracts the place *names* as strings. Geocoding (Photon), distance
(OSRM), the zone check, and the fare math are all deterministic code. So the
NL tab now handles any Mumbai route, exactly like the Route tab, while the LLM
still can't hallucinate a fare or a location — it can only mis-name a place,
which then fails to geocode and is refused rather than guessed.
"""

import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

import geo
from decision import decide_core, Decision
from fare_engine import TimeOfDay

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"
_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


_PARSE_TOOL = {
    "name": "extract_trip",
    "description": "Extract a pickup place, a drop place, and trip context from a natural-language ride query about Mumbai.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pickup": {
                "type": ["string", "null"],
                "description": "The pickup/origin place name as stated (a real Mumbai locality/landmark), or null if none is clearly given.",
            },
            "destination": {
                "type": ["string", "null"],
                "description": "The drop/destination place name as stated, or null if none is clearly given.",
            },
            "extraction_confidence": {
                "type": "string",
                "enum": ["high", "low"],
                "description": "'high' only if BOTH a clear pickup and a clear destination place are present and look like real Mumbai locations.",
            },
            "time_of_day": {
                "type": "string",
                "enum": ["day", "night"],
                "description": "'night' only if a time between 12am-5am is stated or clearly implied; otherwise 'day'.",
            },
            "surge_multiplier": {
                "type": "number",
                "description": "1.0 if nothing implies surge. ~1.3 for moderate signals (rush hour, light rain, 'it's busy'). ~1.5-2.0 for strong signals (heavy rain, festival night, 'surge is crazy').",
            },
            "surge_reasoning": {
                "type": "string",
                "description": "One short clause explaining the surge guess (e.g. 'rush hour + heavy rain').",
            },
        },
        "required": ["extraction_confidence", "time_of_day", "surge_multiplier"],
    },
}


def _parse_query(query: str) -> dict:
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[_PARSE_TOOL],
        tool_choice={"type": "tool", "name": "extract_trip"},
        messages=[{
            "role": "user",
            "content": (
                f"User query: \"{query}\"\n\n"
                f"Extract the pickup and destination place names for this Mumbai ride, plus time "
                f"and surge context. Only set extraction_confidence to 'high' if both a real pickup "
                f"and a real destination in the Mumbai area are clearly present. If a place is "
                f"missing, vague ('my house'), or clearly not in Mumbai (e.g. Delhi, Mars), set "
                f"extraction_confidence to 'low'."
            ),
        }],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return a tool_use block")


def _explain(decision: Decision, route_label: str, params: dict) -> str:
    facts = {
        "route": route_label,
        "time_of_day": params["time_of_day"],
        "surge_multiplier": params["surge_multiplier"],
        "verdict": decision.verdict,
        "confidence": decision.confidence,
        "meter_fare": decision.meter_fare,
        "app_options": [{"provider": q.provider, "tier": q.tier, "fare": q.fare} for q in decision.app_options],
        "savings": decision.savings,
        "reasoning": decision.reasoning,
        "surge_proof_note": decision.surge_proof_note,
        "zone_flag": decision.zone_flag,
        "car_tier_insight": decision.car_tier_insight,
    }
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "You are a terse, friendly Mumbai ride assistant. Given these computed facts "
                "(JSON below), write a short reply (2-4 sentences) for the user's question. "
                "Use ONLY the numbers given — never invent or adjust a rupee figure. "
                "Lead with the verdict. If confidence is 'low' or 'n/a', say so plainly instead "
                "of sounding more certain than the facts support. Mention the car_tier_insight "
                "or surge_proof_note only if present and relevant. Plain text, no markdown, no "
                "rupee symbol issues (write 'Rs.X').\n\n"
                f"Facts:\n{json.dumps(facts, indent=2)}"
            ),
        }],
    )
    return resp.content[0].text


def _refuse(message: str, params: dict) -> dict:
    return {"matched": False, "message": message, "params": params}


def ask(query: str) -> dict:
    """Full pipeline: parse -> geocode -> decide (deterministic) -> explain."""
    params = _parse_query(query)

    pickup = (params.get("pickup") or "").strip()
    dest = (params.get("destination") or "").strip()
    if params.get("extraction_confidence") != "high" or not pickup or not dest:
        return _refuse(
            "I couldn't pull a clear Mumbai pickup and drop from that. Try naming both, "
            "e.g. \"auto from Lokhandwala to Nariman Point at 9pm?\"",
            params,
        )

    # Claude named the places; deterministic code resolves them. A mis-named or
    # non-Mumbai place returns no geocode hit and is refused, not guessed.
    try:
        o_hits = geo.geocode(pickup, limit=1)
        d_hits = geo.geocode(dest, limit=1)
    except Exception:
        return _refuse("The geocoding service is unreachable right now — try again in a moment.", params)

    missing = [name for name, hits in ((pickup, o_hits), (dest, d_hits)) if not hits]
    if missing:
        return _refuse(f"I couldn't find {' or '.join(missing)} as a place in Mumbai. Check the spelling?", params)

    o, d = o_hits[0], d_hits[0]
    dist = geo.route_distance(o.lat, o.lon, d.lat, d.lon)
    dest_in_zone = geo.in_no_auto_zone(d.lat, d.lon)
    origin_in_zone = geo.in_no_auto_zone(o.lat, o.lon)
    zone_restricted = dest_in_zone or origin_in_zone
    zone_place = d.label if dest_in_zone else (o.label if origin_in_zone else d.label)

    tod = TimeOfDay.NIGHT if params["time_of_day"] == "night" else TimeOfDay.DAY
    surge = round(float(params["surge_multiplier"]), 2)
    decision = decide_core(dist["km"], zone_restricted, zone_place, tod, surge)

    route_label = f"{o.label} → {d.label}"
    reply = _explain(decision, route_label, params)

    surge_info = {
        "multiplier": surge,
        "label": "Inferred from your question" if surge != 1.0 else "No surge",
        "reasons": [params.get("surge_reasoning")] if params.get("surge_reasoning") else [],
        "weather_note": "",
        "is_prediction": False,
        "overridden": False,
    }

    return {
        "matched": True,
        "route": {"label": route_label, "origin_label": o.label, "dest_label": d.label},
        "params": params,
        "decision": decision,
        "reply": reply,
        "distance_km": dist["km"],
        "distance_source": dist["source"],
        "time_of_day": tod.value,
        "surge": surge_info,
    }


if __name__ == "__main__":
    test_queries = [
        "should I take an auto from Andheri Station to Versova right now?",
        "is it worth taking an auto to BKC from Bandra at 6pm, traffic seems heavy and surge is crazy",
        "auto from Lokhandwala to Nariman Point around 1am?",   # not a preset; Nariman Point = no-auto zone
        "going from Dadar to Worli, what should I book?",
        "how much from Delhi to Mumbai",                          # out of region -> refuse
        "best way from Mars to Jupiter",                          # gibberish -> refuse
    ]
    for q in test_queries:
        print(f"\n=== Q: {q} ===")
        result = ask(q)
        if result["matched"]:
            print(f"  Route: {result['route']['label']}  ({result['distance_km']} km, {result['distance_source']})")
            print(f"  Parsed: tod={result['params']['time_of_day']} surge={result['params']['surge_multiplier']} ({result['params'].get('surge_reasoning')})")
            print(f"  Verdict: {result['decision'].verdict} [{result['decision'].confidence}]")
            print(f"  Reply: {result['reply']}")
        else:
            print(f"  No match: {result['message']}")
