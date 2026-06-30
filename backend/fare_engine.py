"""
Fare engine: the only layer in this project that produces a number with
zero modeling uncertainty (the RTO meter) alongside numbers that are
necessarily estimates (app fares, since Uber/Ola/Rapido don't publish
rate cards). Keeping that asymmetry visible is the whole point of the
product — see decision.py for how it turns into a confidence rating.
"""

from dataclasses import dataclass
from enum import Enum


class TimeOfDay(str, Enum):
    DAY = "day"
    NIGHT = "night"  # 12 AM - 5 AM, RTO night surcharge window


# --- Source of truth: Maharashtra RTO auto-rickshaw tariff, eff. 1 Feb 2025 ---
RTO_MIN_FARE = 26.0          # covers first 1.5 km
RTO_MIN_FARE_KM = 1.5
RTO_PER_KM = 17.14
RTO_NIGHT_SURCHARGE = 0.25   # +25%, 12 AM - 5 AM

# --- Modeled app rate cards (NOT official — Uber/Ola/Rapido don't publish
# these; calibrated to commonly observed Mumbai fares as of mid-2025).
# App AUTO tiers ride on the same RTO meter + a flat platform fee.
APP_AUTO_PLATFORM_FEE = {
    "Uber Auto": 8.0,
    "Ola Auto": 8.0,
    "Rapido Auto": 5.0,
}

# App CAR tiers have their own base+per-km+per-min structure and a much
# higher minimum fare — this is the gap the product is actually built around.
APP_CAR_RATE_CARDS = {
    "Uber Go": {"base": 50.0, "per_km": 13.0, "per_min": 1.5, "min_fare": 79.0, "free_km": 0},
    "Ola Mini": {"base": 48.0, "per_km": 12.5, "per_min": 1.5, "min_fare": 75.0, "free_km": 0},
}

AVG_SPEED_KMPH_TRAFFIC = 18.0  # assumed avg city speed, used to estimate trip minutes from distance


@dataclass
class FareQuote:
    provider: str
    tier: str  # "auto" | "car"
    fare: float
    is_official_tariff: bool  # True only for the street RTO meter
    note: str = ""


def meter_fare(distance_km: float, time_of_day: TimeOfDay = TimeOfDay.DAY) -> float:
    """Official RTO street-meter fare. Exact, surge-proof, government-fixed."""
    if distance_km <= RTO_MIN_FARE_KM:
        base = RTO_MIN_FARE
    else:
        base = RTO_MIN_FARE + (distance_km - RTO_MIN_FARE_KM) * RTO_PER_KM
    if time_of_day == TimeOfDay.NIGHT:
        base *= (1 + RTO_NIGHT_SURCHARGE)
    return round(base)


def app_auto_fares(distance_km: float, time_of_day: TimeOfDay = TimeOfDay.DAY, surge: float = 1.0) -> list[FareQuote]:
    """App-booked autos: RTO meter + flat platform fee, surged like any app fare."""
    base = meter_fare(distance_km, time_of_day)
    quotes = []
    for provider, fee in APP_AUTO_PLATFORM_FEE.items():
        fare = round((base + fee) * surge)
        quotes.append(FareQuote(
            provider=provider, tier="auto", fare=fare, is_official_tariff=False,
            note="RTO meter + platform fee" + (f" · {surge}x surge" if surge != 1.0 else ""),
        ))
    return quotes


def app_car_fares(distance_km: float, time_of_day: TimeOfDay = TimeOfDay.DAY, surge: float = 1.0) -> list[FareQuote]:
    """App car tiers: modeled base + per-km + per-min, floored at the tier's minimum fare."""
    est_minutes = (distance_km / AVG_SPEED_KMPH_TRAFFIC) * 60
    quotes = []
    for provider, rc in APP_CAR_RATE_CARDS.items():
        raw = rc["base"] + max(0, distance_km - rc["free_km"]) * rc["per_km"] + est_minutes * rc["per_min"]
        fare = max(raw, rc["min_fare"])
        if time_of_day == TimeOfDay.NIGHT:
            fare *= 1.10  # modest modeled night premium for cars (not RTO-regulated, no fixed published %)
        fare = round(fare * surge)
        quotes.append(FareQuote(
            provider=provider, tier="car", fare=fare, is_official_tariff=False,
            note="modeled fare" + (f" · {surge}x surge" if surge != 1.0 else ""),
        ))
    return quotes


def all_fares(distance_km: float, time_of_day: TimeOfDay = TimeOfDay.DAY, surge: float = 1.0) -> dict:
    """Single entry point: street meter (exact) + every modeled app option."""
    return {
        "meter_fare": meter_fare(distance_km, time_of_day),
        "app_options": app_auto_fares(distance_km, time_of_day, surge) + app_car_fares(distance_km, time_of_day, surge),
    }


if __name__ == "__main__":
    scenarios = [
        ("2 km, day, no surge", 2.0, TimeOfDay.DAY, 1.0),
        ("2 km, day, 1.5x surge", 2.0, TimeOfDay.DAY, 1.5),
        ("2 km, night, no surge", 2.0, TimeOfDay.NIGHT, 1.0),
        ("8 km, day, no surge", 8.0, TimeOfDay.DAY, 1.0),
        ("8 km, day, 1.5x surge", 8.0, TimeOfDay.DAY, 1.5),
        ("15 km, day, no surge", 15.0, TimeOfDay.DAY, 1.0),
    ]
    for label, dist, tod, surge in scenarios:
        result = all_fares(dist, tod, surge)
        print(f"\n--- {label} ---")
        print(f"  Meter (official): Rs.{result['meter_fare']}")
        for q in result["app_options"]:
            print(f"  {q.provider:14s} ({q.tier}): Rs.{q.fare:6.0f}  [{q.note}]")
