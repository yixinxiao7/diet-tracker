"""Tests for the Vercel FastAPI adapter in api/index.py."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.lambdas.users import users as users_module
from backend.tests.conftest import FakeConnection, FakeCursor

_INDEX_PATH = Path(__file__).resolve().parents[2] / "api" / "index.py"
_spec = importlib.util.spec_from_file_location("api_index", _INDEX_PATH)
index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(index)


@pytest.fixture
def client():
    return TestClient(index.app)


@pytest.fixture
def recorder(monkeypatch):
    """Replace every route's handler with one that records the event it got."""
    calls = []

    def fake_handler(event, context):
        calls.append(event)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json", "X-From-Handler": "yes"},
            "body": json.dumps({"ok": True}),
        }

    monkeypatch.setattr(
        index, "_ROUTES", [(t, r, fake_handler) for t, r, _ in index._ROUTES]
    )
    return calls


@pytest.fixture
def auth_header(make_token):
    return {"Authorization": f"Bearer {make_token()}"}


# --- route matching ---------------------------------------------------------

@pytest.mark.parametrize("path, template, params, handler", [
    ("/ingredients", "/ingredients", {}, "meals_handler"),
    ("/ingredients/abc", "/ingredients/{id}", {"id": "abc"}, "meals_handler"),
    ("/meals", "/meals", {}, "meals_handler"),
    ("/meals/m-1", "/meals/{id}", {"id": "m-1"}, "meals_handler"),
    ("/meal-logs", "/meal-logs", {}, "meal_logs_handler"),
    ("/meal-logs/l-1", "/meal-logs/{id}", {"id": "l-1"}, "meal_logs_handler"),
    ("/daily-summary", "/daily-summary", {}, "summary_handler"),
    ("/users/bootstrap", "/users/bootstrap", {}, "users_handler"),
    ("/users/me", "/users/me", {}, "users_handler"),
])
def test_match_resource_covers_all_templates(path, template, params, handler):
    matched_template, matched_params, matched_handler = index.match_resource(path)

    assert matched_template == template
    assert matched_params == params
    assert matched_handler is getattr(index, handler)


@pytest.mark.parametrize("path", ["/", "/meals/a/b", "/users", "/nope", "/ingredients/"])
def test_match_resource_rejects_unknown(path):
    assert index.match_resource(path) is None


def test_backend_imports_resolve_from_repo_root():
    assert str(_INDEX_PATH.parents[1]) in __import__("sys").path


# --- event construction -----------------------------------------------------

def test_builds_lambda_event_for_get(client, recorder, auth_header):
    resp = client.get("/api/meals/m-1?limit=5&offset=10", headers=auth_header)

    assert resp.status_code == 201
    assert resp.headers["x-from-handler"] == "yes"
    assert resp.json() == {"ok": True}

    event = recorder[0]
    assert event["httpMethod"] == "GET"
    assert event["resource"] == "/meals/{id}"
    assert event["pathParameters"] == {"id": "m-1"}
    assert event["queryStringParameters"] == {"limit": "5", "offset": "10"}
    assert event["body"] is None
    assert event["headers"]["authorization"] == auth_header["Authorization"]
    assert event["requestContext"]["authorizer"]["claims"] == {
        "sub": "test-auth-user-id",
        "email": "test@example.com",
    }


def test_builds_lambda_event_for_post_body(client, recorder, auth_header):
    client.post("/api/ingredients", headers=auth_header, json={"name": "egg"})

    event = recorder[0]
    assert event["httpMethod"] == "POST"
    assert event["resource"] == "/ingredients"
    assert event["pathParameters"] is None
    assert event["queryStringParameters"] is None
    assert json.loads(event["body"]) == {"name": "egg"}


def test_trailing_slash_is_tolerated(client, recorder, auth_header):
    resp = client.get("/api/users/me/", headers=auth_header, follow_redirects=False)

    assert resp.status_code == 201
    assert recorder[0]["resource"] == "/users/me"


def test_unknown_path_returns_404(client, recorder, auth_header):
    resp = client.get("/api/unknown", headers=auth_header)

    assert resp.status_code == 404
    assert resp.json() == {"error": "Not Found"}
    assert recorder == []


def test_handler_exception_returns_500(client, auth_header, monkeypatch):
    def boom(event, context):
        raise RuntimeError("db down")

    monkeypatch.setattr(index, "_ROUTES", [(t, r, boom) for t, r, _ in index._ROUTES])

    resp = client.get("/api/meals", headers=auth_header)

    assert resp.status_code == 500
    assert resp.json() == {"error": "Internal Server Error"}
    assert "access-control-allow-origin" in resp.headers


def test_preflight_skips_auth(client, recorder):
    resp = client.options("/api/meals", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })

    assert resp.status_code == 204
    assert resp.headers["access-control-allow-origin"] == index.lambda_response(204, None)["headers"]["Access-Control-Allow-Origin"]
    assert "Authorization" in resp.headers["access-control-allow-headers"]
    assert recorder == []


def test_real_handler_end_to_end(client, auth_header, monkeypatch):
    row = (1, "test@example.com", datetime(2024, 1, 2, 3, 4, 5))
    cursor = FakeCursor(fetchone_values=[row])
    monkeypatch.setattr(users_module, "get_connection", lambda: FakeConnection(cursor))

    resp = client.get("/api/users/me", headers=auth_header)

    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"
    query, params = cursor.executed[0]
    assert "auth_user_id" in query
    assert params == ("test-auth-user-id",)


# --- auth -------------------------------------------------------------------

@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": ""},
    {"Authorization": "Bearer"},
    {"Authorization": "Basic abc"},
    {"Authorization": "Bearer not-a-jwt"},
])
def test_protected_routes_reject_missing_or_malformed_token(client, recorder, make_token, headers):
    resp = client.get("/api/meals", headers=headers)

    assert resp.status_code == 401
    assert resp.json() == {"error": "Unauthorized"}
    assert "access-control-allow-origin" in resp.headers
    assert recorder == []


def test_protected_routes_reject_wrong_audience(client, recorder, make_token):
    resp = client.get("/api/meals", headers={"Authorization": f"Bearer {make_token(aud='anon')}"})

    assert resp.status_code == 401
    assert recorder == []


def test_protected_routes_reject_expired_token(client, recorder, make_token):
    resp = client.get("/api/meals", headers={"Authorization": f"Bearer {make_token(exp=1)}"})

    assert resp.status_code == 401
    assert recorder == []


@pytest.mark.parametrize("template", [t for t, _ in index.RESOURCES])
def test_every_resource_requires_auth(client, recorder, make_token, template):
    resp = client.get("/api" + template.replace("{id}", "x"))

    assert resp.status_code == 401
    assert recorder == []


# --- cron -------------------------------------------------------------------

@pytest.fixture
def batch_calls(monkeypatch):
    calls = []

    def fake_batch(event, context):
        calls.append(event)
        return {
            "statusCode": 200,
            "metrics": {"daily_summaries_count": 3, "weekly_reports_count": 1,
                        "anomalies_detected": 0, "errors": []},
        }

    monkeypatch.setattr(index, "daily_summaries_batch_handler", fake_batch)
    monkeypatch.setenv("CRON_SECRET", "s" * 40)
    return calls


def test_cron_runs_batch_with_secret(client, batch_calls):
    resp = client.get("/api/cron/daily-summaries", headers={"Authorization": f"Bearer {'s' * 40}"})

    assert resp.status_code == 200
    assert resp.json()["daily_summaries_count"] == 3
    assert len(batch_calls) == 1


def test_cron_propagates_batch_failure(client, batch_calls, monkeypatch):
    monkeypatch.setattr(index, "daily_summaries_batch_handler", lambda e, c: {
        "statusCode": 500, "metrics": {"errors": ["boom"]},
    })

    resp = client.get("/api/cron/daily-summaries", headers={"Authorization": f"Bearer {'s' * 40}"})

    assert resp.status_code == 500
    assert resp.json()["errors"] == ["boom"]


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong"},
    {"Authorization": "s" * 40},
])
def test_cron_rejects_bad_secret(client, batch_calls, headers):
    resp = client.get("/api/cron/daily-summaries", headers=headers)

    assert resp.status_code == 401
    assert batch_calls == []


def test_cron_rejects_supabase_user_token(client, batch_calls, make_token):
    resp = client.get("/api/cron/daily-summaries", headers={"Authorization": f"Bearer {make_token()}"})

    assert resp.status_code == 401
    assert batch_calls == []


def test_cron_fails_closed_without_secret_configured(client, batch_calls, monkeypatch):
    monkeypatch.delenv("CRON_SECRET")

    resp = client.get("/api/cron/daily-summaries", headers={"Authorization": "Bearer "})

    assert resp.status_code == 401
    assert batch_calls == []


def test_cron_rejects_non_get(client, batch_calls):
    resp = client.post("/api/cron/daily-summaries", headers={"Authorization": f"Bearer {'s' * 40}"})

    assert resp.status_code == 405
    assert batch_calls == []
