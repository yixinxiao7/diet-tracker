import json
from backend.shared.auth import get_user_id
from backend.shared.db import get_connection, get_internal_user_id
from backend.shared.logging import get_logger
from backend.shared.response import response
from backend.shared.validation import is_valid_date, is_valid_uuid

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
    body = json.loads(event.get("body") or "{}")

    meal_id = body.get("meal_id")
    date = body.get("date")
    quantity = body.get("quantity", 1)

    if not meal_id or not date:
        return response(400, {"error": "Missing required fields: meal_id, date"})
    if not is_valid_uuid(meal_id):
        return response(400, {"error": "Invalid ID format"})
    if not is_valid_date(date):
        return response(400, {"error": "Invalid date format"})
    if quantity <= 0:
        return response(400, {"error": "Quantity must be greater than 0"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM meals WHERE id = %s AND user_id = %s",
        (meal_id, user_id)
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
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

    cur.close()
    conn.close()

    logger.info("Created meal log", extra={"user_id": cognito_user_id, "meal_log_id": log_id})
    return response(201, {
        "id": log_id,
        "meal_id": meal_id,
        "date": date,
        "quantity": quantity
    })


def list_meal_logs(event):
    """
    GET /meal-logs?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    cognito_user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date_from = params.get("from")
    date_to = params.get("to")
    try:
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

    filters = ["ml.user_id = %s"]
    args = [user_id]

    if date_from:
        filters.append("ml.date >= %s")
        args.append(date_from)
    if date_to:
        filters.append("ml.date <= %s")
        args.append(date_to)

    where_clause = " AND ".join(filters)

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT ml.id, ml.meal_id, ml.date, ml.quantity, m.name, m.total_calories
        FROM meal_logs ml
        JOIN meals m ON m.id = ml.meal_id
        WHERE {where_clause}
        ORDER BY ml.date DESC, ml.id
        LIMIT %s OFFSET %s
        """,
        tuple(args + [limit, offset])
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

    cur.close()
    conn.close()

    return response(200, {
        "meal_logs": meal_logs
    })


def delete_meal_log(event):
    """
    DELETE /meal-logs/{id}
    """
    cognito_user_id = get_user_id(event)
    log_id = event["pathParameters"]["id"]
    if not is_valid_uuid(log_id):
        return response(400, {"error": "Invalid ID format"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})

    cur = conn.cursor()
    cur.execute(
        "DELETE FROM meal_logs WHERE id = %s AND user_id = %s",
        (log_id, user_id)
    )
    deleted = cur.rowcount
    conn.commit()

    cur.close()
    conn.close()

    if deleted == 0:
        return response(404, {"error": "Meal log not found"})

    logger.info("Deleted meal log", extra={"user_id": cognito_user_id, "meal_log_id": log_id})
    return response(204, None)
