"""
Decision layer: turns fare_engine numbers into a verdict a human can act on.

Core product rule: confidence is calibrated to how close the race is, not
to the rupee amount. A ₹10 gap on a ₹40 trip is a strong signal (25%);
a ₹10 gap on a ₹300 trip is noise (3%). This is also where the
"surge-proof meter" insight falls out for free — surge inflates app fares
but never touches the meter, so high surge mechanically widens the gap
and naturally pushes confidence toward "take the auto" with zero special
casing.
"""

from dataclasses import dataclass
from typing import Optional

from fare_engine import TimeOfDay, all_fares, FareQuote
from routes import get_route

HIGH_CONFIDENCE_GAP = 0.25   # >25% apart -> clear winner
MEDIUM_CONFIDENCE_GAP = 0.10  # 10-25% apart -> lean, not certain
# below 10% -> LOW confidence / toss-up
CAR_TRAP_GAP = 0.20  # car tier >20% pricier than meter -> worth a specific callout


@dataclass
class Decision:
    verdict: str
    confidence: str  # "high" | "medium" | "low" | "n/a"
    meter_fare: Optional[float]
    app_options: list[FareQuote]
    savings: float
    reasoning: str
    surge_proof_note: Optional[str]
    zone_flag: Optional[str]
    car_tier_insight: Optional[str] = None


def _cheapest(options: list[FareQuote]) -> FareQuote:
    return min(options, key=lambda q: q.fare)


def _car_tier_insight(meter: float, app_options: list[FareQuote]) -> Optional[str]:
    """
    The primary verdict compares meter vs the cheapest available app option,
    which is almost always an app-auto (Uber/Ola/Rapido Auto priced near the
    meter) — the honest comparison, but it buries the original insight: most
    people don't open the app and pick the Auto tab, they book whatever's
    default (a car). This surfaces that trap separately when it's large,
    without distorting the primary verdict.
    """
    cars = [q for q in app_options if q.tier == "car"]
    if not cars:
        return None
    cheapest_car = _cheapest(cars)
    gap = (cheapest_car.fare - meter) / meter
    if gap >= CAR_TRAP_GAP:
        diff = round(cheapest_car.fare - meter)
        return (
            f"If you were about to book a car instead: {cheapest_car.provider} runs "
            f"Rs.{cheapest_car.fare} here, Rs.{diff} more than the meter auto. "
            f"Worth checking the auto tab before defaulting to a car on this trip."
        )
    return None


def decide_core(distance_km: float, zone_restricted: bool, dest_name: str,
                time_of_day: TimeOfDay = TimeOfDay.DAY, surge: float = 1.0) -> Decision:
    """
    The actual decision logic, working from a raw distance + zone flag so it
    serves both preset routes and arbitrary geocoded routes. decide() wraps this
    for presets; the /decide_route API path calls it with OSM-derived inputs.
    """
    fares = all_fares(distance_km, time_of_day, surge)
    meter = fares["meter_fare"]
    app_options = fares["app_options"]
    cheapest_app = _cheapest(app_options)

    surge_note = None
    if surge != 1.0:
        surge_note = (
            f"App fares include a {surge}x surge applied to this scenario; the street meter "
            f"is government-fixed and does not change with surge."
        )

    if zone_restricted:
        # Autos aren't a legal option here — no auto-vs-app race to call.
        return Decision(
            verdict=f"Auto not available — book {cheapest_app.provider}",
            confidence="n/a",
            meter_fare=None,
            app_options=app_options,
            savings=0.0,
            reasoning=(
                f"{dest_name} is south of the Bandra (W) / Sion line — Mumbai's "
                f"auto-rickshaw-free zone. Only app cars/autos operate here."
            ),
            surge_proof_note=surge_note,
            zone_flag=f"{dest_name} is in the no-auto zone (South Mumbai / Island City).",
        )

    car_insight = _car_tier_insight(meter, app_options)

    gap = (cheapest_app.fare - meter) / meter  # >0: app pricier than meter; <0: app cheaper

    if abs(gap) >= HIGH_CONFIDENCE_GAP:
        confidence = "high"
    elif abs(gap) >= MEDIUM_CONFIDENCE_GAP:
        confidence = "medium"
    else:
        confidence = "low"

    # Verdict direction is driven by the same threshold as confidence, so the
    # tool never sounds confident ("take the auto") while rating itself "low" —
    # that mismatch is exactly the false-confidence failure mode this is built
    # to avoid. Below MEDIUM_CONFIDENCE_GAP, we say so plainly instead of
    # picking a side.
    savings = round(abs(cheapest_app.fare - meter))
    if confidence == "low":
        verdict = f"Toss-up — meter (Rs.{meter}) and {cheapest_app.provider} (Rs.{cheapest_app.fare}) are within Rs.{savings} of each other"
        reasoning = "The gap is too small to call confidently — go with whichever is in front of you; either choice costs about the same."
    elif gap > 0:
        verdict = f"Take the meter auto — save Rs.{savings} vs {cheapest_app.provider}"
        reasoning = f"Meter auto is Rs.{meter}. Cheapest app option ({cheapest_app.provider}) is Rs.{cheapest_app.fare}."
    else:
        verdict = f"Book {cheapest_app.provider} — save Rs.{savings} vs the meter auto"
        reasoning = f"{cheapest_app.provider} is Rs.{cheapest_app.fare}, cheaper than the Rs.{meter} meter fare."

    return Decision(
        verdict=verdict,
        confidence=confidence,
        meter_fare=meter,
        app_options=app_options,
        savings=savings,
        reasoning=reasoning,
        surge_proof_note=surge_note,
        zone_flag=None,
        car_tier_insight=car_insight,
    )


def decide(route_id: str, time_of_day: TimeOfDay = TimeOfDay.DAY, surge: float = 1.0) -> Decision:
    """Preset-route wrapper around decide_core (back-compat with v1 / evals)."""
    route = get_route(route_id)
    return decide_core(route.distance_km, route.zone_restricted, route.destination, time_of_day, surge)


if __name__ == "__main__":
    scenarios = [
        ("andheri_versova", TimeOfDay.DAY, 1.0),
        ("andheri_versova", TimeOfDay.DAY, 1.5),
        ("andheri_borivali", TimeOfDay.DAY, 1.0),
        ("kurla_powai", TimeOfDay.NIGHT, 1.0),
        ("dadar_worli", TimeOfDay.DAY, 1.0),
        ("bandra_fort", TimeOfDay.DAY, 1.3),
    ]
    for route_id, tod, surge in scenarios:
        d = decide(route_id, tod, surge)
        print(f"\n--- {route_id} | {tod.value} | {surge}x surge ---")
        print(f"  Verdict:    {d.verdict}")
        print(f"  Confidence: {d.confidence}")
        print(f"  Reasoning:  {d.reasoning}")
        if d.surge_proof_note:
            print(f"  Surge note: {d.surge_proof_note}")
        if d.zone_flag:
            print(f"  Zone flag:  {d.zone_flag}")
        if d.car_tier_insight:
            print(f"  Car trap:   {d.car_tier_insight}")
