from backend.shared.response import response
from backend.lambdas.users.users import (
    bootstrap_user,
    get_current_user
)

def handler(event, context):
    method = event.get("httpMethod")
    resource = event.get("resource")

    if not method or not resource:
        return response(400, {"error": "Invalid request"})

    if resource == "/users/bootstrap" and method == "POST":
        return bootstrap_user(event)

    if resource == "/users/me" and method == "GET":
        return get_current_user(event)

    return response(404, {"error": "Not Found"})
