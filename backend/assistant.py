"""
NL assistant layer. Claude does exactly two jobs here, and never a third:

  1. Parse a messy human query ("should I auto to Andheri at 6pm?") into the
     structured inputs the deterministic engine needs: route_id, time_of_day,
     surge_multiplier.
  2. Turn the engine's Decision back into a plain-language reply.

Claude never computes a fare. The actual rupee numbers always come from
fare_engine.py / decision.py — deterministic, reproducible, and grep-able.
This split is the product decision worth defending in an interview: an LLM
hallucinating a fare is the one failure mode this whole project exists to
prevent, so it's structurally impossible here, not just "tested for."
"""

import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from decision import decide, Decision
from fare_engine import TimeOfDay
from routes import list_routes

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"
_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


_PARSE_TOOL = {
    "name": "extract_trip_params",
    "description": "Extract structured trip parameters from a natural-language ride query, matched against a fixed list of known routes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "route_id": {
                "type": ["string", "null"],
                "description": "Best matching route id from the provided list, or null if nothing matches well.",
            },
            "route_match_confidence": {
                "type": "string",
                "enum": ["high", "low", "none"],
                "description": "How sure you are route_id is the route the user meant.",
            },
            "time_of_day": {
                "type": "string",
                "enum": ["day", "night"],
                "description": "'night' only if a time between 12am-5am is stated or clearly implied; default 'day' otherwise.",
            },
            "surge_multiplier": {
                "type": "number",
                "description": "1.0 if nothing implies surge. ~1.3 for moderate signals (rush hour, light rain, 'it's busy'). ~1.5-2.0 for strong signals (heavy rain, festival night, 'surge is crazy').",
            },
            "surge_reasoning": {
                "type": "string",
                "description": "One short clause explaining the surge guess.",
            },
        },
        "required": ["route_match_confidence", "time_of_day", "surge_multiplier"],
    },
}


def _parse_query(query: str) -> dict:
    routes = list_routes()
    routes_text = "\n".join(f"- {r['id']}: {r['label']} ({r['distance_km']} km)" for r in routes)
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[_PARSE_TOOL],
        tool_choice={"type": "tool", "name": "extract_trip_params"},
        messages=[{
            "role": "user",
            "content": (
                f"Known routes:\n{routes_text}\n\n"
                f"User query: \"{query}\"\n\n"
                f"Extract trip parameters. Only set route_match_confidence to 'high' if the "
                f"origin and/or destination clearly correspond to one specific known route."
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


def ask(query: str) -> dict:
    """Full pipeline: parse -> decide (deterministic) -> explain."""
    params = _parse_query(query)

    if params.get("route_match_confidence") != "high" or not params.get("route_id"):
        available = ", ".join(r["label"] for r in list_routes())
        return {
            "matched": False,
            "message": (
                f"I couldn't confidently match that to a known route in this demo. "
                f"Try one of: {available}."
            ),
            "params": params,
        }

    route = next((r for r in list_routes() if r["id"] == params["route_id"]), None)
    if route is None:
        return {
            "matched": False,
            "message": "Claude picked a route_id that isn't in our list — treating as no match.",
            "params": params,
        }

    tod = TimeOfDay.NIGHT if params["time_of_day"] == "night" else TimeOfDay.DAY
    surge = round(float(params["surge_multiplier"]), 2)
    decision = decide(route["id"], tod, surge)
    reply = _explain(decision, route["label"], params)

    return {
        "matched": True,
        "route": route,
        "params": params,
        "decision": decision,
        "reply": reply,
    }


if __name__ == "__main__":
    test_queries = [
        "should I take an auto from Andheri Station to Versova right now?",
        "is it worth taking an auto to BKC from Bandra at 6pm, traffic seems heavy and surge is crazy",
        "I'm at Kurla station heading to Powai around 1am, auto or app?",
        "going from Dadar to Worli, what should I book?",
        "best way from Mars to Jupiter",
    ]
    for q in test_queries:
        print(f"\n=== Q: {q} ===")
        result = ask(q)
        if result["matched"]:
            print(f"  Route: {result['route']['label']}")
            print(f"  Parsed: tod={result['params']['time_of_day']} surge={result['params']['surge_multiplier']} ({result['params'].get('surge_reasoning')})")
            print(f"  Verdict: {result['decision'].verdict} [{result['decision'].confidence}]")
            print(f"  Reply: {result['reply']}")
        else:
            print(f"  No match: {result['message']}")
