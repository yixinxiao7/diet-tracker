import json
from backend.shared.auth import get_user_id
from backend.shared.db import get_connection, get_internal_user_id
from backend.shared.logging import get_logger
from backend.shared.response import response
from backend.shared.validation import (
    is_valid_uuid,
    get_path_param,
    validate_string_length,
    validate_calories,
    MAX_NAME_LENGTH,
    MAX_UNIT_LENGTH,
)

logger = get_logger(__name__)


def create_ingredient(event):
    cognito_user_id = get_user_id(event)
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    name = body.get("name")
    calories_per_unit = body.get("calories_per_unit")
    unit = body.get("unit")

    # Validate name
    name_error = validate_string_length(name, MAX_NAME_LENGTH, "name")
    if name_error:
        return response(400, {"error": name_error})

    # Validate unit
    unit_error = validate_string_length(unit, MAX_UNIT_LENGTH, "unit")
    if unit_error:
        return response(400, {"error": unit_error})

    # Validate calories
    calories_error = validate_calories(calories_per_unit)
    if calories_error:
        return response(400, {"error": calories_error})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, name, calories_per_unit, unit)
        )
        ingredient_id = cur.fetchone()[0]
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return response(201, {
        "id": ingredient_id,
        "name": name,
        "calories_per_unit": calories_per_unit,
        "unit": unit
    })

def list_ingredients(event):
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
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, name, calories_per_unit, unit
            FROM ingredients
            WHERE user_id = %s
            ORDER BY name
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset)
        )
        ingredients = [
            {
                "id": row[0],
                "name": row[1],
                "calories_per_unit": row[2],
                "unit": row[3]
            }
            for row in cur.fetchall()
        ]
    finally:
        cur.close()
        conn.close()

    return response(200, {"ingredients": ingredients})

def update_ingredient(event):
    cognito_user_id = get_user_id(event)
    ingredient_id = get_path_param(event, "id")
    if not is_valid_uuid(ingredient_id):
        return response(400, {"error": "Invalid ID format"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    name = body.get("name")
    calories_per_unit = body.get("calories_per_unit")
    unit = body.get("unit")

    # Validate name
    name_error = validate_string_length(name, MAX_NAME_LENGTH, "name")
    if name_error:
        return response(400, {"error": name_error})

    # Validate unit
    unit_error = validate_string_length(unit, MAX_UNIT_LENGTH, "unit")
    if unit_error:
        return response(400, {"error": unit_error})

    # Validate calories
    calories_error = validate_calories(calories_per_unit)
    if calories_error:
        return response(400, {"error": calories_error})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE ingredients
            SET name = %s, calories_per_unit = %s, unit = %s
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (name, calories_per_unit, unit, ingredient_id, user_id)
        )
        row = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    if not row:
        return response(404, {"error": "Ingredient not found"})

    logger.info("Updated ingredient", extra={"user_id": cognito_user_id, "ingredient_id": ingredient_id})
    return response(200, {
        "id": ingredient_id,
        "name": name,
        "calories_per_unit": calories_per_unit,
        "unit": unit
    })

def delete_ingredient(event):
    cognito_user_id = get_user_id(event)
    ingredient_id = get_path_param(event, "id")
    if not is_valid_uuid(ingredient_id):
        return response(400, {"error": "Invalid ID format"})

    params = event.get("queryStringParameters") or {}
    force = str(params.get("force", "false")).lower() in ("1", "true", "yes")

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        # Verify ingredient belongs to user and check usage count
        cur.execute(
            """
            SELECT COUNT(*)
            FROM meal_ingredients mi
            JOIN ingredients i ON i.id = mi.ingredient_id
            WHERE mi.ingredient_id = %s AND i.user_id = %s
            """,
            (ingredient_id, user_id)
        )
        usage_count = cur.fetchone()[0]
        if usage_count > 0 and not force:
            return response(409, {
                "error": "Ingredient is in use. Remove from meals first or use force=true."
            })

        cur.execute(
            "DELETE FROM ingredients WHERE id = %s AND user_id = %s",
            (ingredient_id, user_id)
        )
        deleted = cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()

    if deleted == 0:
        return response(404, {"error": "Ingredient not found"})

    logger.info("Deleted ingredient", extra={"user_id": cognito_user_id, "ingredient_id": ingredient_id})
    return response(204, None)
