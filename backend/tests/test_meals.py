import json

from backend.lambdas.meals.meals import create_meal, get_meal, list_meals


def test_create_meal_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"name": "Lunch"})
    resp = create_meal(event_copy)
    assert resp["statusCode"] == 400


def test_list_meals_invalid_pagination(event_copy):
    event_copy["queryStringParameters"] = {"limit": "abc"}
    resp = list_meals(event_copy)
    assert resp["statusCode"] == 400


def test_get_meal_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = get_meal(event_copy)
    assert resp["statusCode"] == 400
