from backend.shared.auth import get_user_id
from backend.shared.response import response
from backend.shared.db import get_connection


def get_daily_summary(event):
    """
    GET /daily-summary?date=YYYY-MM-DD
    """
    user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date = params.get("date")
    if not date:
        return response(400, {"error": "Missing required query param: date"})

    conn = get_connection()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return response(200, {
        "date": date,
        "total_calories": total_calories
    })


def get_range_summary(event):
    """
    GET /daily-summary?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    user_id = get_user_id(event)
    params = event.get("queryStringParameters") or {}

    date_from = params.get("from")
    date_to = params.get("to")

    if not date_from or not date_to:
        return response(400, {
            "error": "Missing required query params: from, to"
        })

    conn = get_connection()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return response(200, {
        "from": date_from,
        "to": date_to,
        "days": results
    })
