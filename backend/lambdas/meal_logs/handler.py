import json
from backend.shared.response import response
from backend.lambdas.meal_logs.meal_logs import (
    create_meal_log,
    list_meal_logs,
    delete_meal_log
)


def handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")

    if not method or not resource:
        return response(400, {"error": "Invalid request"})

    if resource == "/meal-logs" and method == "POST":
        return create_meal_log(event)

    if resource == "/meal-logs" and method == "GET":
        return list_meal_logs(event)

    if resource == "/meal-logs/{id}" and method == "DELETE":
        return delete_meal_log(event)

    return response(404, {"error": "Not Found"})
