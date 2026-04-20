"""
Locust load test for the diet-tracker API.

Usage (targeting staging):
    pip install locust
    locust -f loadtests/locustfile.py --host https://<staging-api-url>

Then open http://localhost:8089 and configure users + spawn rate.

For headless runs (e.g., CI):
    locust -f loadtests/locustfile.py \
        --host https://<staging-api-url> \
        --headless -u 10 -r 2 -t 60s \
        --csv=loadtests/results

Environment variables:
    LOCUST_HOST          API base URL (alternative to --host)
    AUTH_TOKEN           Valid Cognito id_token for authenticated requests
    AUTH_BYPASS_TOKEN    If the staging API accepts bypass tokens, set this
"""

import json
import os
import random
import string
from datetime import date, timedelta

from locust import HttpUser, between, events, task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_name(prefix="load", length=6):
    """Generate a short random name for test data."""
    suffix = "".join(random.choices(string.ascii_lowercase, k=length))
    return f"{prefix}-{suffix}"


def random_date(days_back=30):
    """Return a random ISO date string within the last N days."""
    delta = random.randint(0, days_back)
    return (date.today() - timedelta(days=delta)).isoformat()


# ---------------------------------------------------------------------------
# Locust User
# ---------------------------------------------------------------------------

class DietTrackerUser(HttpUser):
    """
    Simulates a typical user session:
      1. Bootstrap user (POST /users/bootstrap)
      2. Browse ingredients and meals
      3. Create an ingredient
      4. Create a meal using that ingredient
      5. Log the meal
      6. Check the daily summary
      7. Clean up (delete log, meal, ingredient)

    Each task is weighted to reflect realistic usage patterns:
    reads are more frequent than writes.
    """

    # Wait 1-3 seconds between tasks (simulates human think time)
    wait_time = between(1, 3)

    def on_start(self):
        """Set up auth headers and bootstrap the user."""
        token = os.environ.get("AUTH_TOKEN") or os.environ.get("AUTH_BYPASS_TOKEN")
        if token:
            token = token.strip()
            self.client.headers.update({"Authorization": f"Bearer {token}"})

        # Track created resource IDs for cleanup
        self._ingredient_ids = []
        self._meal_ids = []
        self._meal_log_ids = []

        # Bootstrap user record
        with self.client.post(
            "/users/bootstrap",
            name="/users/bootstrap",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 401:
                resp.failure("Auth failed — check AUTH_TOKEN env var")
            else:
                resp.failure(f"Bootstrap failed: {resp.status_code}")

    # ------------------------------------------------------------------
    # Read-heavy tasks (higher weight)
    # ------------------------------------------------------------------

    @task(5)
    def list_ingredients(self):
        """GET /ingredients — most common read."""
        self.client.get("/ingredients", name="/ingredients [GET]")

    @task(5)
    def list_meals(self):
        """GET /meals — browse saved meals."""
        self.client.get("/meals", name="/meals [GET]")

    @task(3)
    def list_meal_logs(self):
        """GET /meal-logs — view recent logs."""
        self.client.get("/meal-logs", name="/meal-logs [GET]")

    @task(3)
    def get_daily_summary(self):
        """GET /daily-summary — check today's calorie total."""
        today = date.today().isoformat()
        self.client.get(
            f"/daily-summary?date={today}",
            name="/daily-summary [GET]",
        )

    @task(2)
    def get_daily_summary_range(self):
        """GET /daily-summary with date range — weekly view."""
        end = date.today()
        start = end - timedelta(days=7)
        self.client.get(
            f"/daily-summary?from={start.isoformat()}&to={end.isoformat()}",
            name="/daily-summary [GET range]",
        )

    @task(1)
    def get_user_profile(self):
        """GET /users/me — fetch current user."""
        self.client.get("/users/me", name="/users/me [GET]")

    # ------------------------------------------------------------------
    # Write tasks (lower weight)
    # ------------------------------------------------------------------

    @task(2)
    def create_ingredient(self):
        """POST /ingredients — add a new ingredient."""
        payload = {
            "name": random_name("ing"),
            "calories_per_unit": round(random.uniform(0.5, 10.0), 2),
            "unit": random.choice(["g", "ml", "tbsp", "cup", "oz"]),
        }
        with self.client.post(
            "/ingredients",
            json=payload,
            name="/ingredients [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                ingredient_id = data.get("id") or data.get("ingredient", {}).get("id")
                if ingredient_id:
                    self._ingredient_ids.append(ingredient_id)
                resp.success()
            else:
                resp.failure(f"Create ingredient failed: {resp.status_code}")

    @task(2)
    def create_meal(self):
        """POST /meals — create a meal (requires at least one ingredient)."""
        if not self._ingredient_ids:
            return  # skip if no ingredients created yet

        ingredient_id = random.choice(self._ingredient_ids)
        payload = {
            "name": random_name("meal"),
            "ingredients": [
                {
                    "ingredient_id": ingredient_id,
                    "quantity": random.randint(1, 200),
                }
            ],
        }
        with self.client.post(
            "/meals",
            json=payload,
            name="/meals [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                meal_id = data.get("id") or data.get("meal", {}).get("id")
                if meal_id:
                    self._meal_ids.append(meal_id)
                resp.success()
            else:
                resp.failure(f"Create meal failed: {resp.status_code}")

    @task(2)
    def log_meal(self):
        """POST /meal-logs — log a meal for a random recent date."""
        if not self._meal_ids:
            return  # skip if no meals created yet

        meal_id = random.choice(self._meal_ids)
        payload = {
            "meal_id": meal_id,
            "date": random_date(days_back=7),
            "quantity": random.randint(1, 3),
        }
        with self.client.post(
            "/meal-logs",
            json=payload,
            name="/meal-logs [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                log_id = data.get("id") or data.get("meal_log", {}).get("id")
                if log_id:
                    self._meal_log_ids.append(log_id)
                resp.success()
            else:
                resp.failure(f"Log meal failed: {resp.status_code}")

    # ------------------------------------------------------------------
    # Cleanup tasks (lowest weight — occasional)
    # ------------------------------------------------------------------

    @task(1)
    def delete_meal_log(self):
        """DELETE /meal-logs/:id — remove a random log."""
        if not self._meal_log_ids:
            return
        log_id = self._meal_log_ids.pop(random.randrange(len(self._meal_log_ids)))
        self.client.delete(
            f"/meal-logs/{log_id}",
            name="/meal-logs/:id [DELETE]",
        )

    def on_stop(self):
        """Best-effort cleanup of test data created during the run."""
        for log_id in self._meal_log_ids:
            self.client.delete(f"/meal-logs/{log_id}", name="[cleanup] meal-log")

        for meal_id in self._meal_ids:
            self.client.delete(f"/meals/{meal_id}", name="[cleanup] meal")

        for ing_id in self._ingredient_ids:
            self.client.delete(f"/ingredients/{ing_id}", name="[cleanup] ingredient")


# ---------------------------------------------------------------------------
# Event hooks for summary reporting
# ---------------------------------------------------------------------------

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print a summary line when the test finishes."""
    stats = environment.runner.stats.total
    fail_ratio = stats.fail_ratio if stats.num_requests > 0 else 0
    print(f"\n{'='*60}")
    print(f"  Total requests: {stats.num_requests}")
    print(f"  Failures:       {stats.num_failures} ({fail_ratio:.1%})")
    print(f"  Avg response:   {stats.avg_response_time:.0f}ms")
    print(f"  p95 response:   {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"  p99 response:   {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"  Requests/sec:   {stats.current_rps:.1f}")
    print(f"{'='*60}\n")

    # Fail the run if error rate exceeds 5%
    if fail_ratio > 0.05:
        print("FAIL: Error rate exceeded 5% threshold")
        environment.process_exit_code = 1
