"""
Surge predictor. Replaces v1's manual surge slider, which asked the user to
guess the one thing they can't see. This predicts a surge *likelihood* from
signals we can actually get for free:
  - time of day (rush hours, late-night scarcity)
  - day of week (Fri/Sat nights)
  - live weather (rain is the single biggest surge driver in Mumbai) via
    Open-Meteo, which is free and needs no API key

Critical framing: this is a PREDICTION, never claimed as live/actual surge.
Real-time actual surge has no public source (the hard problem we scoped out).
Presenting a labeled estimate is more honest than either a manual guess or a
false "real-time" claim — same principle as the rest of the tool.
"""

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
MUMBAI_LAT, MUMBAI_LON = 19.076, 72.877
USER_AGENT = "MeterAutos/1.0 (portfolio demo)"

# Weight each signal contributes to the surge multiplier above a 1.0 baseline.
W_RUSH = 0.30
W_LATE_NIGHT = 0.20
W_WEEKEND_NIGHT = 0.15
W_RAIN_LIGHT = 0.30
W_RAIN_HEAVY = 0.60
SURGE_CAP = 2.0


@dataclass
class SurgePrediction:
    multiplier: float
    label: str            # "No surge likely" | "Mild" | "Moderate" | "High surge likely"
    reasons: list = field(default_factory=list)
    weather_note: str = ""
    is_prediction: bool = True   # always True — never live actual surge


def _fetch_rain_mm() -> float:
    """Current precipitation (mm) for Mumbai via Open-Meteo. Fail-soft -> None."""
    params = urllib.parse.urlencode({
        "latitude": MUMBAI_LAT, "longitude": MUMBAI_LON,
        "current": "precipitation", "timezone": "Asia/Kolkata",
    })
    req = urllib.request.Request(f"https://api.open-meteo.com/v1/forecast?{params}",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return float(data.get("current", {}).get("precipitation", 0.0))


def _label_for(mult: float) -> str:
    if mult < 1.15:
        return "No surge likely"
    if mult < 1.35:
        return "Mild surge likely"
    if mult < 1.6:
        return "Moderate surge likely"
    return "High surge likely"


def predict_surge(hour: int = None, weekday: int = None, fetch_weather: bool = True) -> SurgePrediction:
    """
    hour: 0-23 Mumbai local; weekday: 0=Mon..6=Sun. Both default to 'now' (IST).
    """
    now = datetime.now(IST)
    if hour is None:
        hour = now.hour
    if weekday is None:
        weekday = now.weekday()

    mult = 1.0
    reasons = []

    is_rush = hour in (8, 9, 10, 17, 18, 19, 20)
    is_late_night = hour in (0, 1, 2, 3, 4)
    is_weekend_night = weekday in (4, 5) and (hour >= 20 or is_late_night)

    if is_rush:
        mult += W_RUSH
        reasons.append("peak commute hours")
    if is_late_night:
        mult += W_LATE_NIGHT
        reasons.append("late-night driver scarcity")
    if is_weekend_night:
        mult += W_WEEKEND_NIGHT
        reasons.append("weekend night demand")

    weather_note = ""
    if fetch_weather:
        try:
            rain = _fetch_rain_mm()
            if rain >= 2.5:
                mult += W_RAIN_HEAVY
                reasons.append("heavy rain")
                weather_note = f"Heavy rain now ({rain:.1f} mm) — the strongest surge driver in Mumbai."
            elif rain >= 0.3:
                mult += W_RAIN_LIGHT
                reasons.append("rain")
                weather_note = f"Light rain now ({rain:.1f} mm)."
            else:
                weather_note = "Clear now — no weather surge signal."
        except Exception:
            weather_note = "Live weather unavailable — prediction from time of day only."
    else:
        weather_note = "Weather signal skipped."

    mult = round(min(mult, SURGE_CAP), 1)
    if not reasons:
        reasons.append("off-peak, no strong demand signal")

    return SurgePrediction(multiplier=mult, label=_label_for(mult),
                           reasons=reasons, weather_note=weather_note)


if __name__ == "__main__":
    scenarios = [
        ("Weekday 3pm (off-peak)", 15, 2),
        ("Weekday 6pm (rush)", 18, 2),
        ("Weekday 2am (late night)", 2, 2),
        ("Saturday 10pm (weekend night)", 22, 5),
    ]
    print("--- Time/day only (no weather) ---")
    for label, h, wd in scenarios:
        p = predict_surge(hour=h, weekday=wd, fetch_weather=False)
        print(f"  {label:32s} -> {p.multiplier}x  [{p.label}]  ({', '.join(p.reasons)})")

    print("\n--- Live 'now' with real Mumbai weather ---")
    p = predict_surge()
    print(f"  now -> {p.multiplier}x  [{p.label}]")
    print(f"  reasons: {', '.join(p.reasons)}")
    print(f"  weather: {p.weather_note}")
