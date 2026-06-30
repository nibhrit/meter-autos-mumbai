# Step 6 — Evals

## What was built

`evals/eval_set.py` — two separate test sets, because the two halves of the
system have different kinds of uncertainty:
- `DECISION_CASES` (22 cases): route × time-of-day × surge combinations
  spanning short/long trips, day/night, no-surge through 2.0x, and
  zone-restricted routes.
- `NL_CASES` (21 cases): 15 natural-language queries that should match a
  real route (varied phrasing, surge/night signals embedded in the
  sentence), and 6 that should be refused (wrong city, gibberish, an
  unsupported South Mumbai pair).

`evals/run_evals.py` — runs both suites and writes `evals/results.md`.

## Key concept: two different things being evaluated, on purpose

**Part A (decision engine) isn't really an "eval" in the ML sense** — it's
deterministic code, so there's no accuracy to measure against ground truth
from outside the system... except there is one external source of truth:
the published RTO tariff. So the eval re-derives the meter formula
independently inside `run_evals.py` (separate constants, separate function,
not imported from `fare_engine.py`) and re-implements the confidence/
direction classification independently (not imported from `decision.py`),
then checks the real engine's output against both. This is a regression
test against the *spec*, not the implementation testing itself — it would
have caught the step-2 bug (verdict/confidence disagreeing) if it had
existed at eval time.

**Part B (NL layer) is a real eval** — Claude's route-matching has genuine
uncertainty, so this is an actual precision measurement against hand-labeled
ground truth, using live API calls (not mocked).

## Primary metric, applied honestly

CLAUDE.md's chosen primary metric — **high-confidence recommendation
precision** — only has real teeth on the NL layer, since the decision
engine has no uncertainty to be falsely confident about. So it's defined
here as: of every query the assistant matched to a route (which only
happens at `route_match_confidence: "high"` per the gating built in step 3),
what fraction were actually correct. This is exactly the failure mode the
whole project is trying to prevent — a confidently wrong route match — made
measurable.

## Results

- Decision engine: **22/22** passed.
- NL high-confidence precision: **100%** (15/15) — every match was correct.
- Coverage: **100%** (15/15) — every in-scope query was successfully matched.
- Correct refusal rate: **100%** (6/6) — every out-of-scope query was
  declined rather than guessed.

## Honest caveat (flagged in the frontend, not just here)

A clean 100% across 21 NL cases validates the *design* — confidence-gated
refusal works, varied phrasing is handled — but 21 cases is not enough to
claim the assistant is bulletproof. The set doesn't include harder
adversarial cases: typos in location names, or a query mentioning two known
locations in an ambiguous way. Said explicitly in the frontend's Evals
section rather than letting a 100% number imply more rigor than the eval
set actually has — this is the same "don't sound more confident than the
data supports" principle the product is built around, applied to how the
results are reported.

## Verification

Ran the suite for real (`python3 evals/run_evals.py`), including live calls
to the Claude API for all 21 NL cases — not cached, not mocked. Updated the
frontend's Evals section with the actual numbers from this run (previously
a placeholder), verified it renders correctly in browser.
