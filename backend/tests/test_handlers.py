from backend.lambdas.meals import handler as meals_handler
from backend.lambdas.meal_logs import handler as meal_logs_handler
from backend.lambdas.summary import handler as summary_handler
from backend.lambdas.users import handler as users_handler


def test_meals_handler_routes(monkeypatch, event_copy):
    monkeypatch.setattr(meals_handler, "create_meal", lambda *_: {"statusCode": 201})
    event_copy["resource"] = "/meals"
    event_copy["httpMethod"] = "POST"
    resp = meals_handler.handler(event_copy, None)
    assert resp["statusCode"] == 201


def test_meals_handler_not_found(event_copy):
    event_copy["resource"] = "/nope"
    resp = meals_handler.handler(event_copy, None)
    assert resp["statusCode"] == 404


def test_meal_logs_handler_routes(monkeypatch, event_copy):
    monkeypatch.setattr(meal_logs_handler, "list_meal_logs", lambda *_: {"statusCode": 200})
    event_copy["resource"] = "/meal-logs"
    event_copy["httpMethod"] = "GET"
    resp = meal_logs_handler.handler(event_copy, None)
    assert resp["statusCode"] == 200


def test_summary_handler_date_route(monkeypatch, event_copy):
    monkeypatch.setattr(summary_handler, "get_daily_summary", lambda *_: {"statusCode": 200})
    event_copy["resource"] = "/daily-summary"
    event_copy["httpMethod"] = "GET"
    event_copy["queryStringParameters"] = {"date": "2024-01-02"}
    resp = summary_handler.handler(event_copy, None)
    assert resp["statusCode"] == 200


def test_summary_handler_bad_query(event_copy):
    event_copy["resource"] = "/daily-summary"
    event_copy["httpMethod"] = "GET"
    event_copy["queryStringParameters"] = {}
    resp = summary_handler.handler(event_copy, None)
    assert resp["statusCode"] == 400


def test_users_handler_routes(monkeypatch, event_copy):
    monkeypatch.setattr(users_handler, "get_current_user", lambda *_: {"statusCode": 200})
    event_copy["resource"] = "/users/me"
    event_copy["httpMethod"] = "GET"
    resp = users_handler.handler(event_copy, None)
    assert resp["statusCode"] == 200
