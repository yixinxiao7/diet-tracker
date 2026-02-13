from backend.shared.auth import get_user_id
from backend.shared.db import get_connection, get_internal_user_id
from backend.shared.logging import get_logger
from backend.shared.response import response
from backend.shared.validation import is_valid_date

logger = get_logger(__name__)


def get_daily_summary(event):
    """
    GET /daily-summary?date=YYYY-MM-DD
    """
    cognito_user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date = params.get("date")
    if not date:
        return response(400, {"error": "Missing required query param: date"})
    if not is_valid_date(date):
        return response(400, {"error": "Invalid date format"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})
    cur = conn.cursor()

    try:
        query = """
            SELECT
                COALESCE(SUM(m.total_calories * ml.quantity), 0) AS total_calories
            FROM meal_logs ml
            JOIN meals m ON m.id = ml.meal_id
            WHERE ml.user_id = %s
              AND ml.date = %s
        """
        cur.execute(query, (user_id, date))
        total_calories = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()

    logger.info("Fetched daily summary", extra={"user_id": cognito_user_id, "date": date})
    return response(200, {
        "date": date,
        "total_calories": total_calories
    })


def get_range_summary(event):
    """
    GET /daily-summary?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    cognito_user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date_from = params.get("from")
    date_to = params.get("to")

    if not date_from or not date_to:
        return response(400, {
            "error": "Missing required query params: from, to"
        })
    if not is_valid_date(date_from) or not is_valid_date(date_to):
        return response(400, {"error": "Invalid date format"})

    conn = get_connection()
    user_id = get_internal_user_id(conn, cognito_user_id)
    if not user_id:
        conn.close()
        return response(404, {"error": "User not found"})
    cur = conn.cursor()

    try:
        query = """
            SELECT
                ml.date,
                COALESCE(SUM(m.total_calories * ml.quantity), 0) AS total_calories
            FROM meal_logs ml
            JOIN meals m ON m.id = ml.meal_id
            WHERE ml.user_id = %s
              AND ml.date BETWEEN %s AND %s
            GROUP BY ml.date
            ORDER BY ml.date
        """
        cur.execute(query, (user_id, date_from, date_to))

        results = [
            {
                "date": row[0].isoformat(),
                "total_calories": row[1]
            }
            for row in cur.fetchall()
        ]
    finally:
        cur.close()
        conn.close()

    logger.info("Fetched range summary", extra={"user_id": cognito_user_id, "from": date_from, "to": date_to})
    return response(200, {
        "from": date_from,
        "to": date_to,
        "days": results
    })
