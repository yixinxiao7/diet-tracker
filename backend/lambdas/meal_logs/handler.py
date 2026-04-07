import json
from backend.shared.response import response
from backend.shared.logging import get_logger
from backend.shared.metrics import timer, put_count, put_metric
from backend.lambdas.meal_logs.meal_logs import (
    create_meal_log,
    list_meal_logs,
    delete_meal_log
)

logger = get_logger(__name__)


def handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")

    with timer("RequestLatency", dimensions={"Lambda": "meal_logs", "Endpoint": resource or "unknown"}):
        put_count("RequestCount", dimensions={"Lambda": "meal_logs", "Endpoint": resource or "unknown"})

        if not method or not resource:
            logger.info("Invalid request", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meal_logs"})
            return response(400, {"error": "Invalid request"})

        try:
            if resource == "/meal-logs" and method == "POST":
                return create_meal_log(event)

            if resource == "/meal-logs" and method == "GET":
                return list_meal_logs(event)

            if resource == "/meal-logs/{id}" and method == "DELETE":
                return delete_meal_log(event)

            logger.warning("Route not found", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meal_logs"})
            return response(404, {"error": "Not Found"})
        except Exception as e:
            logger.exception("Handler exception", extra={"method": method, "resource": resource, "error": str(e)})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meal_logs"})
            raise
