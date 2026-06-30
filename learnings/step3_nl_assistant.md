# Step 3 — NL Assistant Layer

## What was built

`backend/assistant.py` — a natural-language front door over the deterministic
engine. `ask(query)` runs a 2-call Claude pipeline:
1. **Parse** the free-text query into structured inputs (route_id,
   time_of_day, surge_multiplier) via Claude tool-use (forced tool call,
   so the output is always valid structured JSON, not free text to parse).
2. **Decide** — pure deterministic call into `decision.decide()`. No LLM
   involved.
3. **Explain** — a second Claude call turns the `Decision` object's exact
   numbers into a short plain-language reply.

## Key concept: Claude never computes a fare

This is the load-bearing design decision of the whole layer. Claude's two
jobs are translation (language → structured params, structured facts →
language) — never arithmetic. The explain-step prompt explicitly instructs
"use ONLY the numbers given, never invent or adjust a rupee figure," and
structurally the fare numbers are computed by `decision.py` *before* Claude
ever sees them. This means a fare can never be hallucinated — not because
we trust the model to behave, but because the architecture doesn't give it
the option. This is the single best interview talking point in this layer:
LLMs are good at understanding messy language and bad at trustworthy
arithmetic, so the design routes each job to the right component.

## Key concept: refusing to guess beats guessing wrong

The parse step requires `route_match_confidence: "high"` before the pipeline
proceeds; otherwise it returns a clarification message listing valid routes
instead of picking a plausible-sounding wrong one. Verified with an
adversarial query ("best way from Mars to Jupiter") — correctly refused
rather than silently matching to a random preset route. This mirrors the
project's core principle (don't sound confident when you're not) one layer
up: the assistant shouldn't sound *certain about which route you meant*
when it isn't, any more than the decision engine should sound certain about
price when the gap is small.

## Key concept: the LLM's one legitimate judgment call — surge inference

Surge is a user-selectable *scenario* per scope (no live feed), but in the
NL layer Claude does translate vague human signals ("surge is crazy,"
"1am," "rush hour") into a concrete surge multiplier with a one-line
rationale that's returned alongside the structured params. This is the
correct kind of LLM judgment call: mapping fuzzy language to a structured
input the deterministic engine consumes — not computing the output itself.

## Bug found and fixed during verification

The `car_tier_insight` string in `decision.py` (step 2) hardcoded "don't
default to the car tab on a trip this short" — but the insight fires on any
route where the car-tier gap is ≥20%, including a 7.5 km and a 12.5 km
preset route, which aren't meaningfully "short." Caught by reading the
actual NL reply for the Kurla→Powai (7.5 km) case, not by inspecting code.
Reworded to be distance-agnostic ("worth checking the auto tab before
defaulting to a car"). Reinforces the working-style rule: verify by running
it and reading real output, not by reasoning about the code in the abstract.

## Verification

Ran 5 queries covering: a low-confidence toss-up, a high-surge high-confidence
case (surge correctly inferred from "surge is crazy" + 6pm), a late-night
surge case, a zone-restricted route, and an adversarial out-of-scope query.
All five produced correct route matching (or correct refusal), correct
parameter inference, and replies that accurately reflect the underlying
`Decision` object with no invented numbers.
