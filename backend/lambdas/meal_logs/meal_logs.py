import json
from backend.shared.auth import get_user_id
from backend.shared.db import get_connection, get_internal_user_id
from backend.shared.logging import get_logger
from backend.shared.response import response
from backend.shared.validation import (
    is_valid_date,
    is_valid_uuid,
    get_path_param,
    validate_int_quantity,
)

logger = get_logger(__name__)


def create_meal_log(event):
    """
    POST /meal-logs
    Body:
    {
      "meal_id": "uuid",
      "date": "YYYY-MM-DD",
      "quantity": 1
    }
    """
    cognito_user_id = get_user_id(event)
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    meal_id = body.get("meal_id")
    date = body.get("date")
    quantity = body.get("quantity", 1)

    if not meal_id or not date:
        return response(400, {"error": "Missing required fields: meal_id, date"})
    if not is_valid_uuid(meal_id):
        return response(400, {"error": "Invalid ID format"})
    if not is_valid_date(date):
        return response(400, {"error": "Invalid date format"})

    # Validate quantity with upper bounds
    quantity_error = validate_int_quantity(quantity)
    if quantity_error:
        return response(400, {"error": quantity_error})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM meals WHERE id = %s AND user_id = %s",
            (meal_id, user_id)
        )
        if not cur.fetchone():
            return response(404, {"error": "Meal not found"})

        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, meal_id, date, quantity)
        )
        log_id = cur.fetchone()[0]
        conn.commit()

        logger.info("Created meal log", extra={"user_id": cognito_user_id, "meal_log_id": log_id})
        return response(201, {
            "id": log_id,
            "meal_id": meal_id,
            "date": date,
            "quantity": quantity
        })
    except Exception:
        conn.rollback()
        logger.exception("Failed to create meal log", extra={"user_id": cognito_user_id})
        return response(500, {"error": "Failed to create meal log"})
    finally:
        cur.close()
        conn.close()


def list_meal_logs(event):
    """
    GET /meal-logs?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    cognito_user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date_from = params.get("from")
    date_to = params.get("to")
    try:
        # Default 50, max 100 items
        limit = min(int(params.get("limit", 50)), 100)
        offset = int(params.get("offset", 0))
    except (TypeError, ValueError):
        return response(400, {"error": "Invalid pagination parameters"})
    if limit <= 0 or offset < 0:
        return response(400, {"error": "Invalid pagination parameters"})
    if date_from and not is_valid_date(date_from):
        return response(400, {"error": "Invalid date format"})
    if date_to and not is_valid_date(date_to):
        return response(400, {"error": "Invalid date format"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT ml.id, ml.meal_id, ml.date, ml.quantity, m.name, m.total_calories
            FROM meal_logs ml
            JOIN meals m ON m.id = ml.meal_id
            WHERE ml.user_id = %s
              AND (%s IS NULL OR ml.date >= %s)
              AND (%s IS NULL OR ml.date <= %s)
            ORDER BY ml.date DESC, ml.id
            LIMIT %s OFFSET %s
            """,
            (user_id, date_from, date_from, date_to, date_to, limit, offset)
        )

        meal_logs = [
            {
                "id": row[0],
                "meal_id": row[1],
                "date": row[2].isoformat(),
                "quantity": row[3],
                "meal_name": row[4],
                "meal_calories": row[5]
            }
            for row in cur.fetchall()
        ]

        return response(200, {
            "meal_logs": meal_logs
        })
    except Exception:
        logger.exception("Failed to list meal logs", extra={"user_id": cognito_user_id})
        return response(500, {"error": "Failed to list meal logs"})
    finally:
        cur.close()
        conn.close()


def delete_meal_log(event):
    """
    DELETE /meal-logs/{id}
    """
    cognito_user_id = get_user_id(event)
    log_id = get_path_param(event, "id")
    if not is_valid_uuid(log_id):
        return response(400, {"error": "Invalid ID format"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM meal_logs WHERE id = %s AND user_id = %s",
            (log_id, user_id)
        )
        deleted = cur.rowcount
        conn.commit()

        if deleted == 0:
            return response(404, {"error": "Meal log not found"})

        logger.info("Deleted meal log", extra={"user_id": cognito_user_id, "meal_log_id": log_id})
        return response(204, None)
    except Exception:
        conn.rollback()
        logger.exception("Failed to delete meal log", extra={"user_id": cognito_user_id, "meal_log_id": log_id})
        return response(500, {"error": "Failed to delete meal log"})
    finally:
        cur.close()
        conn.close()
