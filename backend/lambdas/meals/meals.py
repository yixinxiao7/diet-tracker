import json
from backend.shared.auth import get_user_id
from backend.shared.db import get_connection, get_internal_user_id
from backend.shared.logging import get_logger
from backend.shared.response import response
from backend.shared.validation import (
    is_valid_uuid,
    get_path_param,
    validate_string_length,
    validate_quantity,
    MAX_NAME_LENGTH,
)

logger = get_logger(__name__)


def _get_user_id_or_404(conn, cognito_user_id):
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return None, response(404, {"error": "User not found"})
    return user_id, None


def _load_ingredient_calories(cur, user_id, ingredient_ids):
    cur.execute(
        """
        SELECT id, calories_per_unit
        FROM ingredients
        WHERE user_id = %s AND id = ANY(%s)
        """,
        (user_id, ingredient_ids)
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def create_meal(event):
    cognito_user_id = get_user_id(event)
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    name = body.get("name")
    ingredients = body.get("ingredients") or []

    # Validate name
    name_error = validate_string_length(name, MAX_NAME_LENGTH, "name")
    if name_error:
        return response(400, {"error": name_error})

    if not ingredients:
        return response(400, {"error": "At least one ingredient is required"})

    conn = get_connection()
    user_id, error_response = _get_user_id_or_404(conn, cognito_user_id)
    if error_response:
        return error_response

    ingredient_ids = [item.get("ingredient_id") for item in ingredients]
    if not all(ingredient_ids):
        conn.close()
        return response(400, {"error": "Each ingredient requires ingredient_id"})

    # Check for duplicate ingredient IDs
    if len(ingredient_ids) != len(set(ingredient_ids)):
        conn.close()
        return response(400, {"error": "Duplicate ingredient IDs are not allowed"})

    cur = conn.cursor()
    try:
        calories_map = _load_ingredient_calories(cur, user_id, ingredient_ids)
        if len(calories_map) != len(set(ingredient_ids)):
            return response(400, {"error": "Invalid ingredient_id in request"})

        total_calories = 0
        for item in ingredients:
            quantity = item.get("quantity")
            quantity_error = validate_quantity(quantity, "ingredient quantity")
            if quantity_error:
                return response(400, {"error": quantity_error})
            total_calories += calories_map[item["ingredient_id"]] * quantity

        cur.execute("BEGIN")
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, name, total_calories)
        )
        meal_id = cur.fetchone()[0]

        cur.executemany(
            """
            INSERT INTO meal_ingredients (meal_id, ingredient_id, quantity)
            VALUES (%s, %s, %s)
            """,
            [(meal_id, item["ingredient_id"], item["quantity"]) for item in ingredients]
        )
        conn.commit()
        logger.info("Created meal", extra={"user_id": cognito_user_id, "meal_id": meal_id})

        return response(201, {
            "id": meal_id,
            "name": name,
            "total_calories": total_calories
        })
    except Exception:
        conn.rollback()
        logger.exception("Failed to create meal", extra={"user_id": cognito_user_id})
        return response(500, {"error": "Failed to create meal"})
    finally:
        cur.close()
        conn.close()

def list_meals(event):
    cognito_user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}
    try:
        # Default 50, max 100 items
        limit = min(int(params.get("limit", 50)), 100)
        offset = int(params.get("offset", 0))
    except (TypeError, ValueError):
        return response(400, {"error": "Invalid pagination parameters"})
    if limit <= 0 or offset < 0:
        return response(400, {"error": "Invalid pagination parameters"})

    conn = get_connection()
    user_id, error_response = _get_user_id_or_404(conn, cognito_user_id)
    if error_response:
        return error_response

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, name, total_calories, created_at
            FROM meals
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset)
        )
        meals = [
            {
                "id": row[0],
                "name": row[1],
                "total_calories": row[2],
                "created_at": row[3].isoformat()
            }
            for row in cur.fetchall()
        ]
    finally:
        cur.close()
        conn.close()

    return response(200, {"meals": meals})

def get_meal(event):
    cognito_user_id = get_user_id(event)
    meal_id = get_path_param(event, "id")
    if not is_valid_uuid(meal_id):
        return response(400, {"error": "Invalid ID format"})

    conn = get_connection()
    user_id, error_response = _get_user_id_or_404(conn, cognito_user_id)
    if error_response:
        return error_response

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                m.id,
                m.name,
                m.total_calories,
                m.created_at,
                mi.quantity,
                i.id,
                i.name,
                i.calories_per_unit,
                i.unit
            FROM meals m
            LEFT JOIN meal_ingredients mi ON mi.meal_id = m.id
            LEFT JOIN ingredients i ON i.id = mi.ingredient_id
            WHERE m.id = %s AND m.user_id = %s
            ORDER BY i.name
            """,
            (meal_id, user_id)
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    if not rows:
        return response(404, {"error": "Meal not found"})

    meal = {
        "id": rows[0][0],
        "name": rows[0][1],
        "total_calories": rows[0][2],
        "created_at": rows[0][3].isoformat(),
        "ingredients": []
    }

    for row in rows:
        ingredient_id = row[5]
        if ingredient_id:
            meal["ingredients"].append({
                "ingredient_id": ingredient_id,
                "name": row[6],
                "calories_per_unit": row[7],
                "unit": row[8],
                "quantity": row[4]
            })

    return response(200, meal)

def update_meal(event):
    cognito_user_id = get_user_id(event)
    meal_id = get_path_param(event, "id")
    if not is_valid_uuid(meal_id):
        return response(400, {"error": "Invalid ID format"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    name = body.get("name")
    ingredients = body.get("ingredients") or []

    # Validate name
    name_error = validate_string_length(name, MAX_NAME_LENGTH, "name")
    if name_error:
        return response(400, {"error": name_error})

    if not ingredients:
        return response(400, {"error": "At least one ingredient is required"})

    conn = get_connection()
    user_id, error_response = _get_user_id_or_404(conn, cognito_user_id)
    if error_response:
        return error_response

    ingredient_ids = [item.get("ingredient_id") for item in ingredients]
    if not all(ingredient_ids):
        conn.close()
        return response(400, {"error": "Each ingredient requires ingredient_id"})

    # Check for duplicate ingredient IDs
    if len(ingredient_ids) != len(set(ingredient_ids)):
        conn.close()
        return response(400, {"error": "Duplicate ingredient IDs are not allowed"})

    cur = conn.cursor()
    try:
        calories_map = _load_ingredient_calories(cur, user_id, ingredient_ids)
        if len(calories_map) != len(set(ingredient_ids)):
            return response(400, {"error": "Invalid ingredient_id in request"})

        total_calories = 0
        for item in ingredients:
            quantity = item.get("quantity")
            quantity_error = validate_quantity(quantity, "ingredient quantity")
            if quantity_error:
                return response(400, {"error": quantity_error})
            total_calories += calories_map[item["ingredient_id"]] * quantity

        cur.execute("BEGIN")
        cur.execute(
            """
            UPDATE meals
            SET name = %s, total_calories = %s
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (name, total_calories, meal_id, user_id)
        )
        row = cur.fetchone()
        if not row:
            return response(404, {"error": "Meal not found"})

        cur.execute(
            "DELETE FROM meal_ingredients WHERE meal_id = %s",
            (meal_id,)
        )
        cur.executemany(
            """
            INSERT INTO meal_ingredients (meal_id, ingredient_id, quantity)
            VALUES (%s, %s, %s)
            """,
            [(meal_id, item["ingredient_id"], item["quantity"]) for item in ingredients]
        )
        conn.commit()
        logger.info("Updated meal", extra={"user_id": cognito_user_id, "meal_id": meal_id})

        return response(200, {
            "id": meal_id,
            "name": name,
            "total_calories": total_calories
        })
    except Exception:
        conn.rollback()
        logger.exception("Failed to update meal", extra={"user_id": cognito_user_id, "meal_id": meal_id})
        return response(500, {"error": "Failed to update meal"})
    finally:
        cur.close()
        conn.close()

def delete_meal(event):
    cognito_user_id = get_user_id(event)
    meal_id = get_path_param(event, "id")
    if not is_valid_uuid(meal_id):
        return response(400, {"error": "Invalid ID format"})

    conn = get_connection()
    user_id, error_response = _get_user_id_or_404(conn, cognito_user_id)
    if error_response:
        return error_response

    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM meals WHERE id = %s AND user_id = %s",
            (meal_id, user_id)
        )
        deleted = cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()

    if deleted == 0:
        return response(404, {"error": "Meal not found"})

    logger.info("Deleted meal", extra={"user_id": cognito_user_id, "meal_id": meal_id})
    return response(204, None)
