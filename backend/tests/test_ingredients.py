import json

from backend.lambdas.meals.ingredients import (
    create_ingredient,
    delete_ingredient,
    list_ingredients,
    update_ingredient,
)


def test_create_ingredient_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"name": "Salt"})
    resp = create_ingredient(event_copy)
    assert resp["statusCode"] == 400


def test_list_ingredients_invalid_pagination(event_copy):
    event_copy["queryStringParameters"] = {"offset": "-1"}
    resp = list_ingredients(event_copy)
    assert resp["statusCode"] == 400


def test_update_ingredient_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    event_copy["body"] = json.dumps({
        "name": "Salt",
        "calories_per_unit": 0,
        "unit": "g"
    })
    resp = update_ingredient(event_copy)
    assert resp["statusCode"] == 400


def test_delete_ingredient_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = delete_ingredient(event_copy)
    assert resp["statusCode"] == 400
