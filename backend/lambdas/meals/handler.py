import json
from backend.shared.response import response
from backend.shared.logging import get_logger
from backend.shared.metrics import timer, put_count, put_metric

from backend.lambdas.meals.ingredients import (
    create_ingredient,
    list_ingredients,
    update_ingredient,
    delete_ingredient
)
from backend.lambdas.meals.meals import (
    create_meal,
    list_meals,
    get_meal,
    update_meal,
    delete_meal
)

logger = get_logger(__name__)


def handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")

    with timer("RequestLatency", dimensions={"Lambda": "meals", "Endpoint": resource or "unknown"}):
        put_count("RequestCount", dimensions={"Lambda": "meals", "Endpoint": resource or "unknown"})

        if not method or not resource:
            logger.info("Invalid request", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meals"})
            return response(400, {"error": "Invalid request"})

        try:
            # Ingredients
            if resource == "/ingredients" and method == "POST":
                return create_ingredient(event)

            if resource == "/ingredients" and method == "GET":
                return list_ingredients(event)

            if resource == "/ingredients/{id}" and method == "PUT":
                return update_ingredient(event)

            if resource == "/ingredients/{id}" and method == "DELETE":
                return delete_ingredient(event)

            # Meals
            if resource == "/meals" and method == "POST":
                return create_meal(event)

            if resource == "/meals" and method == "GET":
                return list_meals(event)

            if resource == "/meals/{id}" and method == "GET":
                return get_meal(event)

            if resource == "/meals/{id}" and method == "PUT":
                return update_meal(event)

            if resource == "/meals/{id}" and method == "DELETE":
                return delete_meal(event)

            logger.warning("Route not found", extra={"method": method, "resource": resource})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meals"})
            return response(404, {"error": "Not Found"})
        except Exception as e:
            logger.exception("Handler exception", extra={"method": method, "resource": resource, "error": str(e)})
            put_metric("ErrorCount", 1, unit="Count", dimensions={"Lambda": "meals"})
            raise
