"""
Authorization integration tests.

These tests verify that users cannot access, modify, or delete
other users' data. This is critical for security.
"""
import json
import uuid
from datetime import date, datetime
import pytest

from backend.lambdas.meals.ingredients import (
    list_ingredients,
    update_ingredient,
    delete_ingredient,
)
from backend.lambdas.meals.meals import (
    list_meals,
    get_meal,
    update_meal,
    delete_meal,
    create_meal,
)
from backend.lambdas.meal_logs.meal_logs import (
    list_meal_logs,
    delete_meal_log,
    create_meal_log,
)
from backend.lambdas.summary.summary import (
    get_daily_summary,
    get_range_summary,
)


@pytest.fixture
def user_a_data(mock_db_connection, test_user, test_ingredient, test_meal):
    """Data belonging to user A (test_user)."""
    conn, mock_db = mock_db_connection
    # Create a meal log for user A
    meal_log_id = str(uuid.uuid4())
    mock_db["meal_logs"][meal_log_id] = {
        "id": meal_log_id,
        "user_id": test_user["id"],
        "meal_id": test_meal["id"],
        "date": date.today(),
        "quantity": 2
    }

    return {
        "user": test_user,
        "ingredient": test_ingredient,
        "meal": test_meal,
        "meal_log_id": meal_log_id
    }


@pytest.fixture
def user_b(mock_db_connection):
    """Create a second user (user B)."""
    conn, mock_db = mock_db_connection
    user_id = str(uuid.uuid4())
    cognito_id = "user-b-cognito-id"
    email = "userb@example.com"

    mock_db["users"][user_id] = {
        "id": user_id,
        "cognito_user_id": cognito_id,
        "email": email,
        "created_at": datetime.now()
    }

    return {
        "id": user_id,
        "cognito_user_id": cognito_id,
        "email": email
    }


class TestIngredientAuthorization:
    """Test that users cannot access other users' ingredients."""

    def test_list_ingredients_only_shows_own(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not see User A's ingredients."""
        conn, mock_db = mock_db_connection

        # Create an ingredient for user B
        ing_id = str(uuid.uuid4())
        mock_db["ingredients"][ing_id] = {
            "id": ing_id,
            "user_id": user_b["id"],
            "name": "User B Ingredient",
            "calories_per_unit": 50,
            "unit": "g"
        }

        # List as user B
        event = mock_event_factory(
            method="GET",
            resource="/ingredients",
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = list_ingredients(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should only see user B's ingredient
        assert len(body["ingredients"]) == 1
        assert body["ingredients"][0]["name"] == "User B Ingredient"

    def test_update_other_users_ingredient_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to update User A's ingredient."""
        event = mock_event_factory(
            method="PUT",
            resource="/ingredients/{id}",
            path_params={"id": str(user_a_data["ingredient"]["id"])},
            body={
                "name": "Hacked Name",
                "calories_per_unit": 999,
                "unit": "hacked"
            },
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = update_ingredient(event)

        # Should return 404 (ingredient not found for this user)
        assert response["statusCode"] == 404

    def test_delete_other_users_ingredient_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to delete User A's ingredient."""
        conn, mock_db = mock_db_connection
        ingredient_id = user_a_data["ingredient"]["id"]

        event = mock_event_factory(
            method="DELETE",
            resource="/ingredients/{id}",
            path_params={"id": str(ingredient_id)},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = delete_ingredient(event)

        # Should return 404 (ingredient not found for this user)
        assert response["statusCode"] == 404

        # Verify ingredient still exists
        assert ingredient_id in mock_db["ingredients"]


class TestMealAuthorization:
    """Test that users cannot access other users' meals."""

    def test_list_meals_only_shows_own(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not see User A's meals."""
        conn, mock_db = mock_db_connection

        # Create a meal for user B
        meal_id = str(uuid.uuid4())
        mock_db["meals"][meal_id] = {
            "id": meal_id,
            "user_id": user_b["id"],
            "name": "User B Meal",
            "total_calories": 100,
            "created_at": datetime.now()
        }

        # List as user B
        event = mock_event_factory(
            method="GET",
            resource="/meals",
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = list_meals(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should only see user B's meal
        assert len(body["meals"]) == 1
        assert body["meals"][0]["name"] == "User B Meal"

    def test_get_other_users_meal_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to view User A's meal details."""
        event = mock_event_factory(
            method="GET",
            resource="/meals/{id}",
            path_params={"id": str(user_a_data["meal"]["id"])},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = get_meal(event)

        assert response["statusCode"] == 404

    def test_update_other_users_meal_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to update User A's meal."""
        conn, mock_db = mock_db_connection

        # Create an ingredient for user B
        ing_id = str(uuid.uuid4())
        mock_db["ingredients"][ing_id] = {
            "id": ing_id,
            "user_id": user_b["id"],
            "name": "User B Ingredient",
            "calories_per_unit": 50,
            "unit": "g"
        }

        event = mock_event_factory(
            method="PUT",
            resource="/meals/{id}",
            path_params={"id": str(user_a_data["meal"]["id"])},
            body={
                "name": "Hacked Meal",
                "ingredients": [
                    {"ingredient_id": ing_id, "quantity": 1}
                ]
            },
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = update_meal(event)

        assert response["statusCode"] == 404

    def test_delete_other_users_meal_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to delete User A's meal."""
        conn, mock_db = mock_db_connection
        meal_id = user_a_data["meal"]["id"]

        event = mock_event_factory(
            method="DELETE",
            resource="/meals/{id}",
            path_params={"id": str(meal_id)},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = delete_meal(event)

        assert response["statusCode"] == 404

        # Verify meal still exists
        assert meal_id in mock_db["meals"]

    def test_create_meal_with_other_users_ingredient_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to use User A's ingredient in a meal."""
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Stolen Ingredient Meal",
                "ingredients": [
                    {"ingredient_id": str(user_a_data["ingredient"]["id"]), "quantity": 1}
                ]
            },
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = create_meal(event)

        # Should fail because the ingredient doesn't belong to user B
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "invalid" in body["error"].lower()


class TestMealLogAuthorization:
    """Test that users cannot access other users' meal logs."""

    def test_list_meal_logs_only_shows_own(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not see User A's meal logs."""
        conn, mock_db = mock_db_connection

        # Create a meal for user B
        meal_id = str(uuid.uuid4())
        mock_db["meals"][meal_id] = {
            "id": meal_id,
            "user_id": user_b["id"],
            "name": "User B Meal",
            "total_calories": 100,
            "created_at": datetime.now()
        }

        # Create a meal log for user B
        log_id = str(uuid.uuid4())
        mock_db["meal_logs"][log_id] = {
            "id": log_id,
            "user_id": user_b["id"],
            "meal_id": meal_id,
            "date": date.today(),
            "quantity": 1
        }

        # List as user B
        event = mock_event_factory(
            method="GET",
            resource="/meal-logs",
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = list_meal_logs(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should only see user B's log
        assert len(body["meal_logs"]) == 1
        assert body["meal_logs"][0]["meal_name"] == "User B Meal"

    def test_delete_other_users_meal_log_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to delete User A's meal log."""
        conn, mock_db = mock_db_connection
        log_id = user_a_data["meal_log_id"]

        event = mock_event_factory(
            method="DELETE",
            resource="/meal-logs/{id}",
            path_params={"id": str(log_id)},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = delete_meal_log(event)

        assert response["statusCode"] == 404

        # Verify log still exists
        assert log_id in mock_db["meal_logs"]

    def test_create_meal_log_with_other_users_meal_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B should not be able to log User A's meal."""
        event = mock_event_factory(
            method="POST",
            resource="/meal-logs",
            body={
                "meal_id": str(user_a_data["meal"]["id"]),
                "date": date.today().isoformat(),
                "quantity": 1
            },
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = create_meal_log(event)

        # Should fail because the meal doesn't belong to user B
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "meal" in body["error"].lower()


class TestSummaryAuthorization:
    """Test that summaries only include user's own data."""

    def test_daily_summary_only_includes_own_data(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B's daily summary should not include User A's calories."""
        conn, mock_db = mock_db_connection
        today = date.today()

        # Create a meal for user B
        meal_id = str(uuid.uuid4())
        mock_db["meals"][meal_id] = {
            "id": meal_id,
            "user_id": user_b["id"],
            "name": "User B Meal",
            "total_calories": 50,
            "created_at": datetime.now()
        }

        # Create a meal log for user B
        log_id = str(uuid.uuid4())
        mock_db["meal_logs"][log_id] = {
            "id": log_id,
            "user_id": user_b["id"],
            "meal_id": meal_id,
            "date": today,
            "quantity": 1
        }

        # Get daily summary for user B
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"date": today.isoformat()},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = get_daily_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should only include user B's 50 calories, not user A's 400 (200*2)
        assert body["total_calories"] == 50

    def test_range_summary_only_includes_own_data(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b
    ):
        """User B's range summary should not include User A's data."""
        conn, mock_db = mock_db_connection
        today = date.today()

        # Create a meal for user B
        meal_id = str(uuid.uuid4())
        mock_db["meals"][meal_id] = {
            "id": meal_id,
            "user_id": user_b["id"],
            "name": "User B Meal",
            "total_calories": 75,
            "created_at": datetime.now()
        }

        # Create a meal log for user B
        log_id = str(uuid.uuid4())
        mock_db["meal_logs"][log_id] = {
            "id": log_id,
            "user_id": user_b["id"],
            "meal_id": meal_id,
            "date": today,
            "quantity": 1
        }

        # Get range summary for user B
        event = mock_event_factory(
            method="GET",
            resource="/daily-summary",
            query_params={"from": today.isoformat(), "to": today.isoformat()},
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = get_range_summary(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])

        # Should only include user B's data
        assert len(body["days"]) == 1
        assert body["days"][0]["total_calories"] == 75
