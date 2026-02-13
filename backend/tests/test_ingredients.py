import json

from backend.lambdas.meals import ingredients as ingredients_module
from backend.tests.conftest import FakeConnection, FakeCursor


def test_create_ingredient_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"name": "Salt"})
    resp = ingredients_module.create_ingredient(event_copy)
    assert resp["statusCode"] == 400


def test_list_ingredients_invalid_pagination(event_copy):
    event_copy["queryStringParameters"] = {"offset": "-1"}
    resp = ingredients_module.list_ingredients(event_copy)
    assert resp["statusCode"] == 400


def test_update_ingredient_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    event_copy["body"] = json.dumps({
        "name": "Salt",
        "calories_per_unit": 0,
        "unit": "g"
    })
    resp = ingredients_module.update_ingredient(event_copy)
    assert resp["statusCode"] == 400


def test_delete_ingredient_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = ingredients_module.delete_ingredient(event_copy)
    assert resp["statusCode"] == 400


def test_create_ingredient_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[("ing-1",)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(ingredients_module, "get_connection", lambda: conn)
    monkeypatch.setattr(ingredients_module, "get_internal_user_id", lambda *_: 1)

    event_copy["body"] = json.dumps({
        "name": "Rice",
        "calories_per_unit": 100,
        "unit": "g"
    })
    resp = ingredients_module.create_ingredient(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 201
    assert body["id"] == "ing-1"


def test_list_ingredients_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[
        ("ing-1", "Rice", 100, "g"),
        ("ing-2", "Oil", 120, "ml")
    ]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(ingredients_module, "get_connection", lambda: conn)
    monkeypatch.setattr(ingredients_module, "get_internal_user_id", lambda *_: 1)

    resp = ingredients_module.list_ingredients(event_copy)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert len(body["ingredients"]) == 2


def test_update_ingredient_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[("ing-1",)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(ingredients_module, "get_connection", lambda: conn)
    monkeypatch.setattr(ingredients_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    event_copy["body"] = json.dumps({
        "name": "Rice",
        "calories_per_unit": 100,
        "unit": "g"
    })
    resp = ingredients_module.update_ingredient(event_copy)
    assert resp["statusCode"] == 200


def test_delete_ingredient_in_use(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[(2,)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(ingredients_module, "get_connection", lambda: conn)
    monkeypatch.setattr(ingredients_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    resp = ingredients_module.delete_ingredient(event_copy)
    assert resp["statusCode"] == 409


def test_delete_ingredient_force(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[(2,)], rowcount=1)
    conn = FakeConnection(cursor)

    monkeypatch.setattr(ingredients_module, "get_connection", lambda: conn)
    monkeypatch.setattr(ingredients_module, "get_internal_user_id", lambda *_: 1)

    event_copy["pathParameters"] = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    event_copy["queryStringParameters"] = {"force": "true"}
    resp = ingredients_module.delete_ingredient(event_copy)
    assert resp["statusCode"] == 204
