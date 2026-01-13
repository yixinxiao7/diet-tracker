import json
from backend.shared.auth import get_user_id
from backend.shared.response import response


def create_ingredient(event):
    body = json.loads(event["body"])
    return response(201, {"message": "Ingredient created"})

def list_ingredients(event):
    return response(200, {"ingredients": []})

def update_ingredient(event):
    ingredient_id = event["pathParameters"]["id"]
    return response(200, {"message": f"Ingredient {ingredient_id} updated"})

def delete_ingredient(event):
    ingredient_id = event["pathParameters"]["id"]
    return response(204, None)
