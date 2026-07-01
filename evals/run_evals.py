"""
Runs both eval suites and writes evals/results.md.

Part A (decision engine): re-derives the meter fare independently from the
published RTO tariff (not by importing fare_engine's formula) and
independently re-implements the confidence/direction classification (not by
importing decision.py's logic), then checks decision.py's actual output
against both. This is a regression test against the documented spec, not
the implementation testing itself.

Part B (NL layer): the real eval. Runs every query through the live
assistant and scores route-matching against hand-labeled ground truth.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from eval_set import DECISION_CASES, NL_CASES
from fare_engine import all_fares, TimeOfDay
from decision import decide
from assistant import ask as assistant_ask

# Independently re-derived from the published Maharashtra RTO tariff
# (eff. 1 Feb 2025) -- NOT imported from fare_engine.py.
REF_MIN_FARE = 26.0
REF_MIN_FARE_KM = 1.5
REF_PER_KM = 17.14
REF_NIGHT_SURCHARGE = 0.25

HIGH_GAP = 0.25
MEDIUM_GAP = 0.10


def ref_meter_fare(distance_km: float, time_of_day: str) -> int:
    base = REF_MIN_FARE if distance_km <= REF_MIN_FARE_KM else REF_MIN_FARE + (distance_km - REF_MIN_FARE_KM) * REF_PER_KM
    if time_of_day == "night":
        base *= (1 + REF_NIGHT_SURCHARGE)
    return round(base)


def ref_classify(gap: float) -> str:
    if abs(gap) >= HIGH_GAP:
        return "high"
    if abs(gap) >= MEDIUM_GAP:
        return "medium"
    return "low"


def ref_direction(confidence: str, gap: float) -> str:
    if confidence == "low":
        return "tossup"
    return "auto" if gap > 0 else "app"


def verdict_direction(verdict: str) -> str:
    if verdict.startswith("Take the meter auto"):
        return "auto"
    if verdict.startswith("Book "):
        return "app"
    if verdict.startswith("Toss-up"):
        return "tossup"
    if verdict.startswith("Auto not available"):
        return "zone"
    return "unknown"


def run_decision_eval():
    from routes import get_route
    results = []
    for route_id, tod, surge in DECISION_CASES:
        route = get_route(route_id)
        tod_enum = TimeOfDay.NIGHT if tod == "night" else TimeOfDay.DAY
        actual = decide(route_id, tod_enum, surge)

        if route.zone_restricted:
            expected_confidence = "n/a"
            expected_direction = "zone"
        else:
            expected_meter = ref_meter_fare(route.distance_km, tod)
            fares = all_fares(route.distance_km, tod_enum, surge)
            assert fares["meter_fare"] == expected_meter, (
                f"Meter formula mismatch on {route_id}: engine={fares['meter_fare']} ref={expected_meter}"
            )
            cheapest_app = min(fares["app_options"], key=lambda q: q.fare)
            gap = (cheapest_app.fare - expected_meter) / expected_meter
            expected_confidence = ref_classify(gap)
            expected_direction = ref_direction(expected_confidence, gap)

        actual_direction = verdict_direction(actual.verdict)
        passed = (actual.confidence == expected_confidence) and (actual_direction == expected_direction)
        results.append({
            "route_id": route_id, "time_of_day": tod, "surge": surge,
            "expected": (expected_confidence, expected_direction),
            "actual": (actual.confidence, actual_direction),
            "passed": passed,
        })
    return results


def run_nl_eval():
    results = []
    for case in NL_CASES:
        query = case["query"]
        should_match = case["should_match"]
        r = assistant_ask(query)
        matched = r["matched"]
        resolved = r["route"]["label"] if matched else None

        if should_match:
            if not matched:
                outcome = "missed"
            else:
                labels = r["route"]["label"].lower()
                labels_ok = all(sub in labels for sub in case.get("expect_in_labels", []))
                zone_exp = case.get("expect_zone")
                zone_actual = r["decision"].zone_flag is not None
                zone_ok = zone_exp is None or zone_exp == zone_actual
                outcome = "correct_match" if (labels_ok and zone_ok) else (
                    "wrong_zone" if not zone_ok else "wrong_place")
        else:
            outcome = "correct_refusal" if not matched else "false_match"

        results.append({"query": query, "should_match": should_match,
                        "resolved": resolved, "outcome": outcome})
    return results


def summarize(decision_results, nl_results) -> str:
    d_total = len(decision_results)
    d_passed = sum(1 for r in decision_results if r["passed"])

    should_match = [r for r in nl_results if r["should_match"]]
    should_not_match = [r for r in nl_results if not r["should_match"]]
    correct_matches = sum(1 for r in should_match if r["outcome"] == "correct_match")
    correct_refusals = sum(1 for r in should_not_match if r["outcome"] == "correct_refusal")
    all_matched = [r for r in nl_results if r["resolved"] is not None]
    matched_correct = sum(1 for r in all_matched if r["outcome"] == "correct_match")

    coverage = correct_matches / len(should_match) if should_match else 0
    high_conf_precision = matched_correct / len(all_matched) if all_matched else 0
    refusal_rate = correct_refusals / len(should_not_match) if should_not_match else 0

    lines = []
    lines.append("# Eval Results\n")
    lines.append("## Part A — Decision engine regression (deterministic)\n")
    lines.append(f"**{d_passed}/{d_total} passed** — engine output matches independently re-derived RTO formula + documented confidence thresholds.\n")
    if d_passed < d_total:
        lines.append("**Failures:**\n")
        for r in decision_results:
            if not r["passed"]:
                lines.append(f"- {r['route_id']} ({r['time_of_day']}, {r['surge']}x): expected {r['expected']}, got {r['actual']}\n")
    lines.append("\n## Part B — NL assistant, arbitrary Mumbai routes (live Claude + geocoding)\n")
    lines.append("The assistant now resolves any Mumbai pickup/drop (not just presets): Claude extracts "
                  "the place names, deterministic code geocodes them, and a mis-named or non-Mumbai place "
                  "fails to geocode and is refused rather than guessed. A match is 'correct' only if the right "
                  "places resolved AND the no-auto-zone flag is right.\n")
    lines.append(f"- **High-confidence precision (primary metric): {high_conf_precision:.0%}** "
                  f"({matched_correct}/{len(all_matched)}) — of every trip the assistant resolved, how many were "
                  f"correct (right places + right zone call). A confidently-wrong answer is the failure mode this "
                  f"project exists to prevent.\n")
    lines.append(f"- **Coverage (secondary): {coverage:.0%}** ({correct_matches}/{len(should_match)}) — "
                  f"of queries with a real Mumbai pickup+drop, how many resolved correctly instead of punting.\n")
    lines.append(f"- **Correct refusal rate: {refusal_rate:.0%}** ({correct_refusals}/{len(should_not_match)}) — "
                  f"of vague / out-of-region / gibberish queries, how many it declined rather than guessing.\n")
    lines.append("\n**Per-case detail:**\n")
    lines.append("| Query | Should match | Resolved to | Outcome |")
    lines.append("|---|---|---|---|")
    for r in nl_results:
        res = r["resolved"] or "*(refused)*"
        lines.append(f"| {r['query']} | {r['should_match']} | {res} | {r['outcome']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Running decision engine regression suite...")
    decision_results = run_decision_eval()
    d_passed = sum(1 for r in decision_results if r["passed"])
    print(f"  {d_passed}/{len(decision_results)} passed")
    for r in decision_results:
        if not r["passed"]:
            print(f"  FAIL: {r['route_id']} ({r['time_of_day']}, {r['surge']}x) expected={r['expected']} actual={r['actual']}")

    print("\nRunning NL assistant eval (live Claude + geocoding, this takes a bit)...")
    nl_results = run_nl_eval()
    for r in nl_results:
        print(f"  [{r['outcome']:15s}] \"{r['query'][:50]}\" -> {r['resolved']}")

    report = summarize(decision_results, nl_results)
    out_path = os.path.join(os.path.dirname(__file__), "results.md")
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\nWrote {out_path}")
