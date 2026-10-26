# Load Tests

Locust-based load tests for the diet-tracker API.

## Setup

```bash
pip install locust
```

## Running locally (with web UI)

```bash
locust -f loadtests/locustfile.py --host https://diet-tracker.yixinx.com/api
```

Then open http://localhost:8089, set the number of users and spawn rate, and start the test.

## Running headless (CI-friendly)

```bash
export AUTH_TOKEN="<valid-supabase-access-token>"

locust -f loadtests/locustfile.py \
    --host https://diet-tracker.yixinx.com/api \
    --headless \
    -u 10 \
    -r 2 \
    -t 60s \
    --csv=loadtests/results
```

This runs 10 concurrent users, spawning 2 per second, for 60 seconds. Results are written to `loadtests/results_*.csv`.

## Authentication

Set `AUTH_TOKEN` to a valid Supabase access token before running. Grab one from a signed-in session in browser dev tools (the `access_token` in the `sb-<ref>-auth-token` localStorage entry). The API verifies every token, so there is no bypass token.

The host must include the `/api` prefix. A Vercel preview URL works too, but previews share the production Supabase project, so the test data lands in the real database (the test deletes what it creates).

## What it tests

The simulated user session follows a realistic pattern weighted toward reads:

| Task | Weight | Description |
|------|--------|-------------|
| List ingredients | 5 | GET /ingredients |
| List meals | 5 | GET /meals |
| List meal logs | 3 | GET /meal-logs |
| Daily summary | 3 | GET /daily-summary (single day) |
| Summary range | 2 | GET /daily-summary (7-day range) |
| User profile | 1 | GET /users/me |
| Create ingredient | 2 | POST /ingredients |
| Create meal | 2 | POST /meals |
| Log meal | 2 | POST /meal-logs |
| Delete log | 1 | DELETE /meal-logs/:id |

## Pass/fail criteria

The test exits with code 1 if the overall error rate exceeds 5%.
