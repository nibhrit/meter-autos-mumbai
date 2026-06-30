# Step 4 — FastAPI App

## What was built

`backend/main.py` — three endpoints wiring the previous layers to HTTP:
- `GET /routes` — lists preset routes (frontend uses this to populate the
  route picker, no hardcoding distances client-side).
- `POST /decide` — structured input (`route_id`, `time_of_day`, `surge`) →
  the deterministic `Decision`, serialized to JSON. No LLM call in this path.
- `POST /ask` — free-text `query` → the full NL assistant pipeline.
- `GET /health` — trivial liveness check, useful once this is deployed.

CORS is wide open (`allow_origins=["*"]`) — fine and intentional for a
single-purpose portfolio demo with no auth or user data, not something to
carry into a real product.

## Why two input paths instead of one

`/decide` and `/ask` exist side by side deliberately: `/decide` is the fast,
free, deterministic path a real frontend control (dropdowns for route/time/
surge) would use on every interaction; `/ask` is the natural-language path
that costs an LLM call and is for the "type your question" demo experience.
Keeping them separate means the deterministic core is independently testable
and the frontend doesn't pay for an LLM call just to render a dropdown
result.

## Verification

Ran the server locally (`uvicorn`) and hit all four endpoints with `curl`,
reading actual responses rather than assuming the code was correct:
- `/health` and `/routes` return expected shapes.
- `/decide` with a valid route + surge returns the full Decision JSON,
  matching what `decision.py`'s standalone test printed in step 2.
- `/decide` with an unknown `route_id` correctly returns HTTP 404 (the
  `ValueError` from `routes.get_route()` is caught and translated).
- `/ask` with a zone-restricted query ("CST to Colaba") correctly returns
  `matched: true`, `confidence: "n/a"`, and a reply that doesn't claim a
  meter fare exists where one legally can't.

## Note for next step

Added `backend/requirements.txt` (fastapi, uvicorn, anthropic, python-dotenv,
pydantic) pinned to currently-installed versions, needed for the eventual
Render deployment step.
