from datetime import datetime, timedelta, date
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def compute_daily_summaries(conn, target_date=None):
    """
    Compute daily summaries for all users with meal logs on target_date.

    Args:
        conn: Database connection
        target_date: Date to compute summaries for (defaults to yesterday)

    Returns:
        Count of summaries created/updated
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    cur = conn.cursor()

    try:
        # Query to get all users with meal logs on target_date and their calorie totals
        query = """
            SELECT
                ml.user_id,
                COALESCE(SUM(m.total_calories * ml.quantity), 0) AS total_calories,
                COUNT(DISTINCT ml.id) AS meal_count
            FROM meal_logs ml
            JOIN meals m ON m.id = ml.meal_id
            WHERE ml.date = %s
            GROUP BY ml.user_id
        """

        cur.execute(query, (target_date,))
        results = cur.fetchall()

        # UPSERT into daily_summaries
        upsert_query = """
            INSERT INTO daily_summaries (user_id, date, total_calories, meal_count, computed_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, date)
            DO UPDATE SET
                total_calories = EXCLUDED.total_calories,
                meal_count = EXCLUDED.meal_count,
                computed_at = CURRENT_TIMESTAMP
        """

        count = 0
        for user_id, total_calories, meal_count in results:
            cur.execute(upsert_query, (user_id, target_date, total_calories, meal_count))
            count += 1

        conn.commit()
        logger.info(f"Computed {count} daily summaries", extra={"target_date": str(target_date)})
        return count

    finally:
        cur.close()


def compute_weekly_reports(conn, target_date=None):
    """
    Compute weekly reports for the ISO week containing target_date.

    Args:
        conn: Database connection
        target_date: Date whose week to compute (defaults to yesterday)

    Returns:
        Count of weekly reports created/updated
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    # Get ISO week info
    # Python's isocalendar returns (year, week_num, weekday)
    iso_year, iso_week, _ = target_date.isocalendar()

    # Calculate week_start (Monday) and week_end (Sunday)
    week_start = datetime.strptime(f"{iso_year}-W{iso_week:02d}-1", "%G-W%V-%u").date()
    week_end = week_start + timedelta(days=6)

    cur = conn.cursor()

    try:
        # Query to get all users with daily_summaries in that week
        query = """
            SELECT
                user_id,
                AVG(total_calories) AS avg_daily_calories,
                MIN(total_calories) AS min_daily_calories,
                MAX(total_calories) AS max_daily_calories,
                SUM(meal_count) AS total_meals
            FROM daily_summaries
            WHERE date BETWEEN %s AND %s
            GROUP BY user_id
        """

        cur.execute(query, (week_start, week_end))
        results = cur.fetchall()

        # UPSERT into weekly_reports
        upsert_query = """
            INSERT INTO weekly_reports (user_id, week_start, week_end, avg_daily_calories, min_daily_calories, max_daily_calories, total_meals, computed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, week_start)
            DO UPDATE SET
                week_end = EXCLUDED.week_end,
                avg_daily_calories = EXCLUDED.avg_daily_calories,
                min_daily_calories = EXCLUDED.min_daily_calories,
                max_daily_calories = EXCLUDED.max_daily_calories,
                total_meals = EXCLUDED.total_meals,
                computed_at = CURRENT_TIMESTAMP
        """

        count = 0
        for user_id, avg_cal, min_cal, max_cal, total_meals in results:
            cur.execute(
                upsert_query,
                (user_id, week_start, week_end, avg_cal, min_cal, max_cal, total_meals)
            )
            count += 1

        conn.commit()
        logger.info(
            f"Computed {count} weekly reports",
            extra={"week_start": str(week_start), "week_end": str(week_end)}
        )
        return count

    finally:
        cur.close()


def detect_anomalies(conn, target_date=None):
    """
    Detect calorie anomalies (spikes > 50% above rolling average) for target_date.

    Args:
        conn: Database connection
        target_date: Date to check for anomalies (defaults to yesterday)

    Returns:
        List of anomalies detected (each is a dict with user_id, daily_calories, rolling_avg, deviation_percent)
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    cur = conn.cursor()
    anomalies = []

    try:
        # Get all users with daily summaries on target_date
        query = """
            SELECT user_id, total_calories
            FROM daily_summaries
            WHERE date = %s
        """

        cur.execute(query, (target_date,))
        results = cur.fetchall()

        for user_id, daily_calories in results:
            # Calculate 30-day rolling average (excluding target_date)
            rolling_query = """
                SELECT AVG(total_calories) AS rolling_avg
                FROM daily_summaries
                WHERE user_id = %s
                  AND date < %s
                  AND date >= %s
            """

            rolling_start = target_date - timedelta(days=30)
            cur.execute(rolling_query, (user_id, target_date, rolling_start))
            rolling_result = cur.fetchone()

            rolling_avg = rolling_result[0] if rolling_result[0] is not None else daily_calories

            # Check if current day is > 50% above rolling average
            if rolling_avg > 0:
                deviation_percent = ((daily_calories - rolling_avg) / rolling_avg) * 100
            else:
                deviation_percent = 0

            if daily_calories > rolling_avg * 1.5:
                # Insert anomaly
                anomaly_insert = """
                    INSERT INTO nutrition_anomalies (user_id, date, daily_calories, rolling_avg_calories, deviation_percent, created_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """

                cur.execute(
                    anomaly_insert,
                    (user_id, target_date, daily_calories, rolling_avg, deviation_percent)
                )

                anomalies.append({
                    "user_id": user_id,
                    "daily_calories": daily_calories,
                    "rolling_avg_calories": rolling_avg,
                    "deviation_percent": deviation_percent
                })

        conn.commit()
        logger.info(
            f"Detected {len(anomalies)} anomalies",
            extra={"target_date": str(target_date), "count": len(anomalies)}
        )
        return anomalies

    finally:
        cur.close()
