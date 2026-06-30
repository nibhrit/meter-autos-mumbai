# Interview Talking Points — Meter Autos

Grounded in what was actually built. Use these as raw material, not a script.

---

## 30-second pitch

"Mumbai's auto-rickshaw meter is government-fixed and published — exact, surge-proof, no
guessing. Uber/Ola/Rapido pricing is proprietary and dynamic — it can only ever be estimated.
I built a tool that's honest about that asymmetry: a confident verdict when the price gap is
wide, and a plain 'toss-up, here's your surge-proof anchor' when it isn't — instead of giving
a confident-looking number either way, which is what every existing comparator does."

---

## The reframe story (market research → product judgment)

**Situation:** Initial idea was "an app to compare meter-auto fares against Uber/Ola/Rapido in
Mumbai." Did market research before writing any code.

**Complication:** Found MeterSahi — a tool that already does almost exactly this. A screenshot
of it showed: meter ₹366 vs Uber/Ola/Rapido Auto at ₹371–374. A ₹5–8 gap. The "obvious" version
of the idea was already built, and worse, the price gap that justifies it barely exists.

**The insight, not just the pivot:** Read the screenshot more carefully instead of just accepting
defeat. MeterSahi's app-fare numbers were modeled as `meter + flat platform fee` with hedges like
"excl. surge" and "always check the app before booking" — i.e. it gives a confident green
"CHEAPEST" badge built on a number it admits is wrong exactly when the decision matters most
(surge). That's the actual gap in an occupied market: not "nobody compares fares," but "nobody
is honest about when they're sure."

**Action:** Reframed from "build a comparator" to "build a confidence-calibrated decision tool."
Confirmed the new center of gravity with the user before writing code (asked: does this land,
or different angle) rather than assuming.

**Why this is the strongest interview story here:** It demonstrates the actual PM skill —
finding competitors doesn't end the analysis, it sharpens it. The product became *better*, not
just different, because of the research.

---

## Key product decisions (each defensible on its own)

### 1. Confidence is calibrated to gap size, not trip distance or surge state
**Decision:** HIGH confidence above a 25% price gap, MEDIUM 10–25%, LOW below 10% — based on the
percentage gap between the meter and the cheapest app option, full stop.
**Why:** Considered distance-band (hardcode "short trips = confident") and a surge-hybrid rule.
Rejected both because they bake in assumptions about *why* a gap exists. Letting the data decide
when to sound confident is the more honest design — and it's simpler.
**Bonus, found after building it:** The surge-proof insight ("the meter is your anchor when
surge hits") wasn't hand-coded. Surge inflates app fares; the meter never moves; gap-based
confidence picks that up automatically. Verified in testing: at 1.0x surge a route was LOW
confidence (toss-up), at 1.5x surge the *same route* flipped to HIGH confidence "take the auto" —
zero special-case code for surge.

### 2. A bug caught by reading actual output, not by reasoning about code
**What happened:** Early version could say "Take the meter auto" (a confident directive) while
also labeling itself "low confidence" — a 9% gap triggered the directive-wording branch but the
confidence-tier branch separately. Contradictory messaging, the exact failure mode the project
exists to prevent.
**Fix:** Made verdict *direction* gated by the same threshold as confidence, so below the medium
cutoff the tool says "toss-up," never picks a side.
**Why it matters for the story:** Found by running the code and reading the printed output across
scenarios, not by code review. Reinforces a working principle: verify locally, don't assume
correctness from logic alone.

### 3. The "car-tab trap" — recovering the original thesis without compromising honesty
**Tension:** The most honest primary comparison (meter vs. *cheapest available* app option) is
almost always meter vs. app-auto — a small, undramatic gap. That's correct, but it quietly buried
the original pitch: most people don't open the app and tap the Auto tab, they book whatever's
default (a car), and *that* gap is large on short trips.
**Resolution:** Didn't change the primary verdict (would have made it less honest). Added a
*secondary* call-out — "if you were about to book a car instead, you'd pay ₹X more" — that fires
only when the car-tier gap is large. Recovers the real insight without polluting the primary
number.
**Why this is a good interview answer:** Shows the difference between a quick fix and resolving
the actual tension between two valid product goals (honesty vs. the original insight) by adding
the right structure, not by picking one and dropping the other.

### 4. The LLM never computes a fare — structurally, not by instruction
**Decision:** Claude has exactly two jobs: parse messy language into structured inputs
(route, time, surge), and turn structured output back into plain language. The actual rupee
arithmetic happens in a separate deterministic Python layer the LLM never touches.
**Why this is the single best AI-product answer in this build:** It's not "we prompted the model
to be careful with numbers" — the architecture makes fare hallucination structurally impossible,
because the model is never given the opportunity to produce a number that reaches the user
unverified. This is the right way to think about LLM reliability in a product: don't trust
behavior, design away the failure mode.

### 5. Refusing to guess beats guessing wrong, one layer up
**Decision:** The NL layer requires high-confidence route matching before answering at all;
otherwise it returns "I couldn't confidently match that" with a list of valid options.
**Verification:** Tested with an adversarial query ("best way from Mars to Jupiter") — correctly
refused instead of fuzzy-matching to a plausible-sounding wrong route.
**Why it matters:** Same principle as the core thesis, applied one layer up — the assistant
shouldn't sound certain about *which route you meant* when it isn't, any more than the engine
should sound certain about *price* when the gap is small.

### 6. Zone restrictions are a distinct code path, not a confidence=0 hack
**Decision:** Routes inside Mumbai's no-auto zone (south of Bandra/Sion) skip the verdict
entirely — confidence is `"n/a"`, not computed and floored at zero.
**Why:** A tool that fakes running the math and getting zero confidence is lying about what it
did. A tool that says "this comparison doesn't apply here, here's why" is being honest about its
own boundaries.

---

## Eval design and metric choice

**Two separate eval suites, because the two halves of the system have different kinds of
uncertainty:**
- The decision engine is deterministic — there's nothing to measure "accuracy" against except
  the published spec. So the eval re-derives the RTO meter formula *independently* (separate
  code, not imported) and checks the real engine against it — a regression test against the
  spec, not the implementation testing itself.
- The NL layer has real uncertainty — Claude's route-matching can be wrong. That's where an
  actual precision metric belongs.

**Primary metric: high-confidence recommendation precision.** Of every route the assistant
matched with confidence, how many were actually correct. Chosen because the failure mode that
destroys trust in this product isn't "didn't have an answer" — it's "sounded sure and was
wrong." Directly mirrors the fraud-detection framing of "false positive rate matters more than
raw accuracy": a confidently wrong answer is worse than an honest non-answer.

**Result and how it was reported:** 100% across both suites (22/22 deterministic, 15/15 NL
matches, 6/6 correct refusals). Reported with an explicit caveat in the UI itself: 21 NL cases
validates the *design* (confidence-gating works), not a claim of bulletproof reliability — harder
adversarial cases (typos, ambiguous multi-location queries) are the natural next eval to add.
**Why this caveat matters as an interview point:** Applying the same "don't sound more confident
than the data supports" principle to how *I* communicate results, not just how the product does.

---

## Scope cuts (and why each one is defensible, not just "ran out of time")

| Cut | Why |
|---|---|
| Live app-fare scraping/APIs | No public API exists for Uber/Ola/Rapido pricing; scraping is legally grey. Modeled fares instead, clearly labeled as estimates — the honest version of "we don't have this data." |
| Live maps/geocoding | Curated preset routes keep the demo deterministic and reliable instead of dependent on a third external API and live traffic data. |
| Live surge feed | Surge is a user-selectable scenario. Keeps the demo reliable while still proving the surge-proof-meter insight, which doesn't require live data — it requires showing the *mechanism*. |

---

## Anticipated interview questions this story answers

- *"Tell me about a time research changed your product direction."* → The MeterSahi reframe.
- *"How do you think about trust in an AI-powered product?"* → The LLM-never-computes-a-fare
  architecture + the refuse-to-guess NL gating.
- *"How do you choose a success metric?"* → High-confidence precision over raw accuracy, and why.
- *"Tell me about a bug you caught."* → The confidence/verdict-direction mismatch, caught by
  reading real output.
- *"Tell me about reconciling two things in tension."* → The car-tab trap insight vs. primary
  verdict honesty.
- *"How do you scope a v1?"* → The three scope cuts table, each with a real reason, not just
  "didn't get to it."
