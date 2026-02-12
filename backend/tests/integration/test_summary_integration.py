"""Integration tests for summary endpoints."""
import json
from datetime import date, timedelta
import pytest

from backend.lambdas.summary.summary import (
    get_daily_summary,
    get_range_summary,
)


class TestGetDailySummary:
    """Integration tests for GET /daily-summary?date=YYYY-MM-DD."""

    def test_daily_summary_no_logs(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        today = date.today().isoformat()
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"date": today},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["date"] == today
        assert body["total_calories"] == 0

    def test_daily_summary_with_logs(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        today = date.today()

        # Create meal logs for today
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (test_user["id"], test_meal["id"], today, 2)  # 200 cal * 2 = 400
        )
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (test_user["id"], test_meal["id"], today, 1)  # 200 cal * 1 = 200
        )
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"date": today.isoformat()},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["total_calories"] == 600  # 400 + 200

    def test_daily_summary_missing_date(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "date" in body["error"].lower()

    def test_daily_summary_invalid_date_format(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"date": "01-15-2024"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "date" in body["error"].lower()

    def test_daily_summary_user_not_found(
        self, mock_db_connection, mock_event_factory
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"date": date.today().isoformat()},
            cognito_user_id="non-existent-user"
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 404


class TestGetRangeSummary:
    """Integration tests for GET /daily-summary?from=YYYY-MM-DD&to=YYYY-MM-DD."""

    def test_range_summary_no_logs(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()

        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": from_date, "to": to_date},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["from"] == from_date
        assert body["to"] == to_date
        assert body["days"] == []

    def test_range_summary_with_logs(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Create meal logs for multiple days
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (test_user["id"], test_meal["id"], today, 2)  # 400 cal
        )
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (test_user["id"], test_meal["id"], yesterday, 1)  # 200 cal
        )
        db_connection.commit()
        cur.close()

        from_date = yesterday.isoformat()
        to_date = today.isoformat()

        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": from_date, "to": to_date},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["days"]) == 2

        # Results should be ordered by date
        assert body["days"][0]["date"] == yesterday.isoformat()
        assert body["days"][0]["total_calories"] == 200
        assert body["days"][1]["date"] == today.isoformat()
        assert body["days"][1]["total_calories"] == 400

    def test_range_summary_aggregates_per_day(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        """Test that multiple logs on the same day are aggregated."""
        today = date.today()

        # Create multiple meal logs for the same day
        cur = db_connection.cursor()
        for _ in range(3):
            cur.execute(
                """
                INSERT INTO meal_logs (user_id, meal_id, date, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                (test_user["id"], test_meal["id"], today, 1)  # 200 cal each
            )
        db_connection.commit()
        cur.close()

        from_date = today.isoformat()
        to_date = today.isoformat()

        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": from_date, "to": to_date},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["days"]) == 1
        assert body["days"][0]["total_calories"] == 600  # 200 * 3

    def test_range_summary_missing_from(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"to": date.today().isoformat()},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "from" in body["error"].lower()

    def test_range_summary_missing_to(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": date.today().isoformat()},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 400

    def test_range_summary_invalid_from_date(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": "invalid", "to": date.today().isoformat()},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 400

    def test_range_summary_invalid_to_date(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": date.today().isoformat(), "to": "invalid"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 400

    def test_range_summary_user_not_found(
        self, mock_db_connection, mock_event_factory
    ):
        today = date.today()
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": today.isoformat(), "to": today.isoformat()},
            cognito_user_id="non-existent-user"
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 404
