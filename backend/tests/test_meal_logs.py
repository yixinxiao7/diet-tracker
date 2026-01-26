import json

from backend.lambdas.meal_logs.meal_logs import (
    create_meal_log,
    delete_meal_log,
    list_meal_logs,
)


def test_create_meal_log_missing_fields(event_copy):
    event_copy["body"] = json.dumps({"meal_id": "123"})
    resp = create_meal_log(event_copy)
    assert resp["statusCode"] == 400


def test_create_meal_log_invalid_date(event_copy):
    event_copy["body"] = json.dumps({
        "meal_id": "123e4567-e89b-12d3-a456-426614174000",
        "date": "2024/01/02"
    })
    resp = create_meal_log(event_copy)
    assert resp["statusCode"] == 400


def test_list_meal_logs_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024/01/02"}
    resp = list_meal_logs(event_copy)
    assert resp["statusCode"] == 400


def test_delete_meal_log_invalid_id(event_copy):
    event_copy["pathParameters"] = {"id": "invalid"}
    resp = delete_meal_log(event_copy)
    assert resp["statusCode"] == 400
