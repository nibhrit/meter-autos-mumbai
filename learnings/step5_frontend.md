# Step 5 — Frontend

## What was built

`frontend/index.html` — single-page demo: hero (the reframe pitch), how-it-works
(3 steps), tech stack cards (one per backend layer), live demo (route-picker
tab + NL-ask tab), an evals section (placeholder until step 6), disclaimer
strip, footer with repo link. Vanilla JS, no framework, no build step —
portfolio-shareable as one file.

`frontend/serve.py` — a minimal static file server, kept in the repo for
local dev (`python3 serve.py`).

## Design decisions

- **Dropdowns lead, NL is secondary** (confirmed with the user): the route/
  time/surge picker hits `/decide` instantly with no API cost; the NL tab
  hits `/ask`, which costs a Claude call. Leading with the free, instant
  path is the right default; NL is there to show off the assistant layer
  specifically, not as the primary interaction.
- **The verdict card's color directly encodes confidence** (green=high,
  amber=medium, grey=low/n/a) — the visual language reinforces the same
  point as the text: this tool only looks confident when it is.
- **`decisionCardHtml()` returns a string instead of writing to the DOM
  directly.** First draft had it write directly, which forced an awkward
  double-write workaround in the NL tab (set reply, overwrite with
  decision, then re-prepend reply). Refactored once the awkwardness was
  visible in code review, before it shipped.

## Infra problem hit and worked around

The built-in preview tool's server launcher runs in a stricter macOS
sandbox that can't access paths under `~/Desktop` at all (TCC protection) —
confirmed by testing increasingly explicit configs (relative path, absolute
path, custom server) and getting `PermissionError`/`Operation not permitted`
every time, even though the same commands work fine when run directly via
the Bash tool. Worked around by starting both the backend (`uvicorn`) and
the static frontend server (`serve.py`) via Bash directly, then driving and
verifying the actual page through the Chrome browser tools (navigate, click,
type, screenshot, read console) instead of the preview tool. This is the
kind of environment quirk worth knowing for future sessions in this project.

## Verification

Ran both servers locally and drove the real page in a browser (not just
read the code):
- Confirmed `/routes` populates the dropdown correctly on load, no console
  errors.
- Clicked "Get verdict" at no surge → correct low-confidence toss-up card,
  car-tier insight visible, fare table populated.
- Switched surge to 1.5x, re-ran → confidence visibly flips to high (green),
  surge-proof note appears — same behavior verified at the API level in
  step 2, now confirmed rendering correctly end-to-end through the UI.
- Used the NL tab with a real query ("...BKC from Bandra at 6pm, surge is
  crazy right now") → correct route match, correct surge inference, plain-
  language reply, and a decision card with matching numbers underneath —
  full pipeline (browser → FastAPI → Claude parse → decision engine →
  Claude explain → browser) confirmed working live, not just unit-tested
  per layer.
- Checked browser console throughout: zero errors or warnings.

## Pending

`API_BASE` in `index.html` is currently hardcoded to
`http://127.0.0.1:8000` for local testing — needs to be updated to the
Render URL once the backend is deployed (user is setting that up via the
Render dashboard with the `render.yaml` blueprint pushed in step 4).
