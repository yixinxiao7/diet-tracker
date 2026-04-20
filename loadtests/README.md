# Load Tests

Locust-based load tests for the diet-tracker API.

## Setup

```bash
pip install locust
```

## Running locally (with web UI)

```bash
locust -f loadtests/locustfile.py --host https://<your-staging-api-url>
```

Then open http://localhost:8089, set the number of users and spawn rate, and start the test.

## Running headless (CI-friendly)

```bash
export AUTH_TOKEN="<valid-cognito-id-token>"

locust -f loadtests/locustfile.py \
    --host https://<your-staging-api-url> \
    --headless \
    -u 10 \
    -r 2 \
    -t 60s \
    --csv=loadtests/results
```

This runs 10 concurrent users, spawning 2 per second, for 60 seconds. Results are written to `loadtests/results_*.csv`.

## Authentication

Set one of these environment variables before running:

- `AUTH_TOKEN` — a valid Cognito `id_token` (use browser dev tools to grab one from a logged-in session)
- `AUTH_BYPASS_TOKEN` — if the staging environment has `VITE_AUTH_BYPASS` enabled

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
