import json
from datetime import date

from backend.lambdas.meal_logs import meal_logs as meal_logs_module
from backend.tests.conftest import FakeConnection, FakeCursor


def test_create_meal_log_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"meal_id": "123"})
    resp = meal_logs_module.create_meal_log(event_copy)
    assert resp["statusCode"] == 400


def test_create_meal_log_invalid_date(event_copy):
    event_copy["body"] = json.dumps({
        "meal_id": "123e4567-e89b-12d3-a456-426614174000",
        "date": "2024/01/02"
    })
    resp = meal_logs_module.create_meal_log(event_copy)
    assert resp["statusCode"] == 400


def test_list_meal_logs_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024/01/02"}
    resp = meal_logs_module.list_meal_logs(event_copy)
    assert resp["statusCode"] == 400


def test_delete_meal_log_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = meal_logs_module.delete_meal_log(event_copy)
    assert resp["statusCode"] == 400


def test_create_meal_log_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[("meal-1",), ("log-1",)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meal_logs_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meal_logs_module, "get_internal_user_id", lambda *_: 1)

    event_copy["body"] = json.dumps({
        "meal_id": "123e4567-e89b-12d3-a456-426614174000",
        "date": "2024-01-02",
        "quantity": 1
    })
    resp = meal_logs_module.create_meal_log(event_copy)
    assert resp["statusCode"] == 201
    assert conn.committed is True


def test_list_meal_logs_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[
        ("log-1", "meal-1", date(2024, 1, 2), 1, "Lunch", 300)
    ]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meal_logs_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meal_logs_module, "get_internal_user_id", lambda *_: 1)

    resp = meal_logs_module.list_meal_logs(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["meal_logs"][0]["meal_name"] == "Lunch"


def test_delete_meal_log_success(monkeypatch, event_copy):
    cursor = FakeCursor(rowcount=1)
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meal_logs_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meal_logs_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    resp = meal_logs_module.delete_meal_log(event_copy)
    assert resp["statusCode"] == 204
