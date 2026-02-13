from backend.shared.auth import get_user_id
from backend.shared.response import response
from backend.shared.db import get_connection

from backend.lambdas.summary.summary import (
    get_daily_summary,
    get_range_summary
)


def handler(event, context):
    resource = event.get("resource")
    method = event.get("httpMethod")
    params = event.get("queryStringParameters") or {}

    if not method or not resource:
        return response(400, {"error": "Invalid request"})

    if resource == "/daily-summary" and method == "GET":
        if "date" in params:
            return get_daily_summary(event)
        if "from" in params and "to" in params:
            return get_range_summary(event)

        return response(400, {
            "error": "Expected query params: date OR from & to"
        })

    return response(404, {"error": "Not Found"})
