"""Integration tests for meal_logs endpoints."""
import json
from datetime import date, timedelta
import pytest

from backend.lambdas.meal_logs.meal_logs import (
    create_meal_log,
    list_meal_logs,
    delete_meal_log,
)


class TestCreateMealLog:
    """Integration tests for POST /meal-logs."""

    def test_create_meal_log_success(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        today = date.today().isoformat()
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": today,
                "quantity": 1
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["meal_id"] == str(test_meal["id"])
        assert body["date"] == today
        assert body["quantity"] == 1
        assert "id" in body

    def test_create_meal_log_with_quantity(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        today = date.today().isoformat()
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": today,
                "quantity": 3
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["quantity"] == 3

    def test_create_meal_log_missing_fields(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={"meal_id": "123e4567-e89b-12d3-a456-426614174000"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "required" in body["error"].lower()

    def test_create_meal_log_invalid_date_format(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": "01-15-2024",  # Wrong format
                "quantity": 1
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "date" in body["error"].lower()

    def test_create_meal_log_invalid_meal_id(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": "not-a-uuid",
                "date": date.today().isoformat(),
                "quantity": 1
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400

    def test_create_meal_log_meal_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": "123e4567-e89b-12d3-a456-426614174000",
                "date": date.today().isoformat(),
                "quantity": 1
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "meal" in body["error"].lower()

    def test_create_meal_log_invalid_quantity_zero(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": date.today().isoformat(),
                "quantity": 0
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "quantity" in body["error"].lower()

    def test_create_meal_log_invalid_quantity_negative(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": date.today().isoformat(),
                "quantity": -1
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400

    def test_create_meal_log_quantity_exceeds_max(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": date.today().isoformat(),
                "quantity": 20000
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "exceed" in body["error"].lower()

    def test_create_meal_log_quantity_must_be_integer(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": date.today().isoformat(),
                "quantity": 1.5
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "integer" in body["error"].lower()

    def test_create_meal_log_quantity_boolean_rejected(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(test_meal["id"]),
                "date": date.today().isoformat(),
                "quantity": True
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal_log(event)

        assert response["statusCode"] == 400


class TestListMealLogs:
    """Integration tests for GET /meal-logs."""

    def test_list_meal_logs_empty(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["meal_logs"] == []

    def test_list_meal_logs_with_data(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        # Create a meal log
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (test_user["id"], test_meal["id"], date.today(), 1)
        )
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["meal_logs"]) == 1
        assert body["meal_logs"][0]["meal_name"] == "Test Meal"

    def test_list_meal_logs_filter_by_date_range(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        # Create meal logs for multiple dates
        cur = db_connection.cursor()
        today = date.today()
        for i in range(5):
            log_date = today - timedelta(days=i)
            cur.execute(
                """
                INSERT INTO meal_logs (user_id, meal_id, date, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                (test_user["id"], test_meal["id"], log_date, 1)
            )
        db_connection.commit()
        cur.close()

        # Filter to last 2 days
        from_date = (today - timedelta(days=1)).isoformat()
        to_date = today.isoformat()

        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            query_params={"from": from_date, "to": to_date},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["meal_logs"]) == 2

    def test_list_meal_logs_invalid_date_format(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            query_params={"from": "invalid-date"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 400

    def test_list_meal_logs_pagination(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        # Create multiple meal logs
        cur = db_connection.cursor()
        today = date.today()
        for i in range(10):
            cur.execute(
                """
                INSERT INTO meal_logs (user_id, meal_id, date, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                (test_user["id"], test_meal["id"], today, 1)
            )
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            query_params={"limit": "5", "offset": "3"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["meal_logs"]) == 5


class TestDeleteMealLog:
    """Integration tests for DELETE /meal-logs/{id}."""

    def test_delete_meal_log_success(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, db_connection
    ):
        # Create a meal log to delete
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (test_user["id"], test_meal["id"], date.today(), 1)
        )
        log_id = cur.fetchone()[0]
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="DELETE",
            resource="/meal-logs/{id}",
            path_params={"id": str(log_id)},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal_log(event)

        assert response["statusCode"] == 204

        # Verify deletion
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM meal_logs WHERE id = %s", (log_id,))
        assert cur.fetchone() is None
        cur.close()

    def test_delete_meal_log_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/meal-logs/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal_log(event)

        assert response["statusCode"] == 404

    def test_delete_meal_log_invalid_id(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/meal-logs/{id}",
            path_params={"id": "invalid-uuid"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal_log(event)

        assert response["statusCode"] == 400
