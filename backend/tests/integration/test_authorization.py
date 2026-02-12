"""
Authorization integration tests.

These tests verify that users cannot access, modify, or delete
other users' data. This is critical for security.
"""
import json
from datetime import date
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
def user_a_data(db_connection, test_user, test_ingredient, test_meal):
    """Data belonging to user A (test_user)."""
    # Create a meal log for user A
    cur = db_connection.cursor()
    cur.execute(
        """
        INSERT INTO meal_logs (user_id, meal_id, date, quantity)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (test_user["id"], test_meal["id"], date.today(), 2)
    )
    meal_log_id = cur.fetchone()[0]
    db_connection.commit()
    cur.close()

    return {
        "user": test_user,
        "ingredient": test_ingredient,
        "meal": test_meal,
        "meal_log_id": meal_log_id
    }


@pytest.fixture
def user_b(db_connection, clean_tables):
    """Create a second user (user B)."""
    cur = db_connection.cursor()
    cur.execute(
        """
        INSERT INTO users (cognito_user_id, email)
        VALUES (%s, %s)
        RETURNING id, cognito_user_id, email
        """,
        ("user-b-cognito-id", "userb@example.com")
    )
    row = cur.fetchone()
    db_connection.commit()
    cur.close()

    return {
        "id": row[0],
        "cognito_user_id": row[1],
        "email": row[2]
    }


class TestIngredientAuthorization:
    """Test that users cannot access other users' ingredients."""

    def test_list_ingredients_only_shows_own(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not see User A's ingredients."""
        # Create an ingredient for user B
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            """,
            (user_b["id"], "User B Ingredient", 50, "g")
        )
        db_connection.commit()
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not be able to delete User A's ingredient."""
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
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM ingredients WHERE id = %s", (ingredient_id,))
        assert cur.fetchone() is not None
        cur.close()


class TestMealAuthorization:
    """Test that users cannot access other users' meals."""

    def test_list_meals_only_shows_own(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not see User A's meals."""
        # Create a meal for user B
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            """,
            (user_b["id"], "User B Meal", 100)
        )
        db_connection.commit()
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not be able to update User A's meal."""
        # Create an ingredient for user B to use
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_b["id"], "User B Ingredient", 50, "g")
        )
        user_b_ingredient_id = cur.fetchone()[0]
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="PUT",
            resource="/meals/{id}",
            path_params={"id": str(user_a_data["meal"]["id"])},
            body={
                "name": "Hacked Meal",
                "ingredients": [
                    {"ingredient_id": str(user_b_ingredient_id), "quantity": 1}
                ]
            },
            cognito_user_id=user_b["cognito_user_id"]
        )

        response = update_meal(event)

        assert response["statusCode"] == 404

    def test_delete_other_users_meal_fails(
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not be able to delete User A's meal."""
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
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM meals WHERE id = %s", (meal_id,))
        assert cur.fetchone() is not None
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not see User A's meal logs."""
        # Create a meal and log for user B
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_b["id"], "User B Meal", 100)
        )
        user_b_meal_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (user_b["id"], user_b_meal_id, date.today(), 1)
        )
        db_connection.commit()
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B should not be able to delete User A's meal log."""
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
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM meal_logs WHERE id = %s", (log_id,))
        assert cur.fetchone() is not None
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B's daily summary should not include User A's calories."""
        today = date.today()

        # Create a meal and log for user B
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_b["id"], "User B Meal", 50)
        )
        user_b_meal_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (user_b["id"], user_b_meal_id, today, 1)  # 50 calories
        )
        db_connection.commit()
        cur.close()

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
        self, mock_db_connection, mock_event_factory, user_a_data, user_b, db_connection
    ):
        """User B's range summary should not include User A's data."""
        today = date.today()

        # Create a meal and log for user B
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_b["id"], "User B Meal", 75)
        )
        user_b_meal_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_id, date, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (user_b["id"], user_b_meal_id, today, 1)
        )
        db_connection.commit()
        cur.close()

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
