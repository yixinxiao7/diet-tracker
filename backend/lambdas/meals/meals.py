import json
from backend.shared.auth import get_user_id
from backend.shared.response import response


def create_meal(event):
    body = json.loads(event["body"])
    return response(201, {"message": "Meal created"})

def list_meals(event):
    return response(200, {"meals": []})

def get_meal(event):
    meal_id = event["pathParameters"]["id"]
    return response(200, {"meal_id": meal_id})

def update_meal(event):
    meal_id = event["pathParameters"]["id"]
    body = json.loads(event["body"])
    return response(200, {"message": f"Meal {meal_id} updated"})

def delete_meal(event):
    meal_id = event["pathParameters"]["id"]
    return response(204, None)