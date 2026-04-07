from backend.shared.response import response
from backend.shared.logging import get_logger
from backend.shared.metrics import timer, put_count, put_metric
from backend.lambdas.users.users import (
    bootstrap_user,
    get_current_user
)

logger = get_logger(__name__)


def handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")

    with timer("RequestLatency", dimensions={"Lambda": "users", "Endpoint": resource or "unknown"}):
        put_count("RequestCount", dimensions={"Lambda": "users", "Endpoint": resource or "unknown"})

        if not method or not resource:
            logger.info("Invalid request", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "users"})
            return response(400, {"error": "Invalid request"})

        try:
            if resource == "/users/bootstrap" and method == "POST":
                return bootstrap_user(event)

            if resource == "/users/me" and method == "GET":
                return get_current_user(event)

            logger.warning("Route not found", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "users"})
            return response(404, {"error": "Not Found"})
        except Exception as e:
            logger.exception("Handler exception", extra={"method": method, "resource": resource, "error": str(e)})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "users"})
            raise
