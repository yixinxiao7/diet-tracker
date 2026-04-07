from backend.shared.auth import get_user_id
from backend.shared.response import response
from backend.shared.db import get_connection
from backend.shared.logging import get_logger
from backend.shared.metrics import timer, put_count, put_metric

from backend.lambdas.summary.summary import (
    get_daily_summary,
    get_range_summary
)

logger = get_logger(__name__)


def handler(event, context):
    resource = event.get("resource")
    method = event.get("httpMethod")
    params = event.get("queryStringParameters") or {}

    with timer("RequestLatency", dimensions={"Lambda": "summary", "Endpoint": resource or "unknown"}):
        put_count("RequestCount", dimensions={"Lambda": "summary", "Endpoint": resource or "unknown"})

        if not method or not resource:
            logger.info("Invalid request", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "summary"})
            return response(400, {"error": "Invalid request"})

        try:
            if resource == "/daily-summary" and method == "GET":
                if "date" in params:
                    return get_daily_summary(event)
                if "from" in params and "to" in params:
                    return get_range_summary(event)

                logger.warning("Missing query parameters for daily-summary", extra={"params": list(params.keys())})
                put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "summary"})
                return response(400, {
                    "error": "Expected query params: date OR from & to"
                })

            logger.warning("Route not found", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "summary"})
            return response(404, {"error": "Not Found"})
        except Exception as e:
            logger.exception("Handler exception", extra={"method": method, "resource": resource, "error": str(e)})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "summary"})
            raise
