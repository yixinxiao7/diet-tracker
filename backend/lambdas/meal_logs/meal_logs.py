import json
from backend.shared.auth import get_user_id
from backend.shared.response import response


def create_meal_log(event):
    """
    POST /meal-logs
    Body:
    {
      "meal_id": "uuid",
      "date": "YYYY-MM-DD",
      "quantity": 1
    }
    """
    user_id = get_user_id(event)
    body = json.loads(event["body"])

    meal_id = body["meal_id"]
    date = body["date"]
    quantity = body.get("quantity", 1)

    # TODO: Insert into meal_logs table
    # (user_id, meal_id, date, quantity)

    return response(201, {
        "message": "Meal logged successfully"
    })


def list_meal_logs(event):
    """
    GET /meal-logs?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date_from = params.get("from")
    date_to = params.get("to")

    # TODO: Query meal_logs table filtered by user_id + date range

    return response(200, {
        "meal_logs": []
    })


def delete_meal_log(event):
    """
    DELETE /meal-logs/{id}
    """
    user_id = get_user_id(event)
    log_id = event["pathParameters"]["id"]

    # TODO: Delete meal_log where id = log_id AND user_id = user_id

    return response(204, None)

