import json
from backend.shared.response import response

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


def handler(event, context):
    method = event["httpMethod"]
    resource = event["resource"]

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

    return response(404, {"error": "Not Found"})
