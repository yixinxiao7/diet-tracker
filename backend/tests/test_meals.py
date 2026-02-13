import json
from datetime import datetime

from backend.lambdas.meals import meals as meals_module
from backend.tests.conftest import FakeConnection, FakeCursor


def test_create_meal_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"name": "Lunch"})
    resp = meals_module.create_meal(event_copy)
    assert resp["statusCode"] == 400


def test_list_meals_invalid_pagination(event_copy):
    event_copy["queryStringParameters"] = {"limit": "abc"}
    resp = meals_module.list_meals(event_copy)
    assert resp["statusCode"] == 400


def test_get_meal_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = meals_module.get_meal(event_copy)
    assert resp["statusCode"] == 400


def test_load_ingredient_calories():
    cursor = FakeCursor(fetchall_values=[[("id1", 10), ("id2", 20)]])
    result = meals_module._load_ingredient_calories(cursor, 1, ["id1", "id2"])
    assert result == {"id1": 10, "id2": 20}


def test_get_user_id_or_404_not_found(monkeypatch):
    conn = FakeConnection(FakeCursor())
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: None)
    user_id, error = meals_module._get_user_id_or_404(conn, "cognito")
    assert user_id is None
    assert error["statusCode"] == 404
    assert conn.closed is True


def test_create_meal_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[("meal-1",)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)
    monkeypatch.setattr(meals_module, "_load_ingredient_calories", lambda *_: {"ing-1": 100})

    event_copy["body"] = json.dumps({
        "name": "Lunch",
        "ingredients": [{"ingredient_id": "ing-1", "quantity": 2}]
    })
    resp = meals_module.create_meal(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 201
    assert body["total_calories"] == 200
    assert conn.committed is True


def test_create_meal_failure_rolls_back(monkeypatch, event_copy):
    cursor = FakeCursor(raise_on_execute=RuntimeError("boom"))
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)

    event_copy["body"] = json.dumps({
        "name": "Lunch",
        "ingredients": [{"ingredient_id": "ing-1", "quantity": 2}]
    })
    resp = meals_module.create_meal(event_copy)
    assert resp["statusCode"] == 500
    assert conn.rolled_back is True


def test_list_meals_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[
        ("meal-1", "Lunch", 300, datetime(2024, 1, 1, 12, 0, 0))
    ]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)

    resp = meals_module.list_meals(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["meals"][0]["name"] == "Lunch"


def test_get_meal_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[
        ("meal-1", "Lunch", 300, datetime(2024, 1, 1, 12, 0, 0), 2, "ing-1", "Rice", 150, "g"),
        ("meal-1", "Lunch", 300, datetime(2024, 1, 1, 12, 0, 0), None, None, None, None, None)
    ]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    resp = meals_module.get_meal(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert len(body["ingredients"]) == 1


def test_get_meal_not_found(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    resp = meals_module.get_meal(event_copy)
    assert resp["statusCode"] == 404


def test_update_meal_not_found(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[None])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)
    monkeypatch.setattr(meals_module, "_load_ingredient_calories", lambda *_: {"ing-1": 100})

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    event_copy["body"] = json.dumps({
        "name": "Lunch",
        "ingredients": [{"ingredient_id": "ing-1", "quantity": 2}]
    })
    resp = meals_module.update_meal(event_copy)
    assert resp["statusCode"] == 404


def test_delete_meal_success(monkeypatch, event_copy):
    cursor = FakeCursor(rowcount=1)
    conn = FakeConnection(cursor)

    monkeypatch.setattr(meals_module, "get_connection", lambda: conn)
    monkeypatch.setattr(meals_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    resp = meals_module.delete_meal(event_copy)
    assert resp["statusCode"] == 204
