"""Integration tests for meals endpoints."""
import json
import pytest

from backend.lambdas.meals.meals import (
    create_meal,
    list_meals,
    get_meal,
    update_meal,
    delete_meal,
)


class TestCreateMeal:
    """Integration tests for POST /meals."""

    def test_create_meal_success(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Lunch",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 2}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["name"] == "Lunch"
        assert body["total_calories"] == 200  # 100 cal * 2 quantity
        assert "id" in body

    def test_create_meal_multiple_ingredients(
        self, mock_db_connection, mock_event_factory, test_user, db_connection
    ):
        # Create two ingredients
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (test_user["id"], "Ingredient A", 100, "g")
        )
        ing_a = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (test_user["id"], "Ingredient B", 50, "g")
        )
        ing_b = cur.fetchone()[0]
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Mixed Meal",
                "ingredients": [
                    {"ingredient_id": str(ing_a), "quantity": 2},
                    {"ingredient_id": str(ing_b), "quantity": 3}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["total_calories"] == 350  # (100*2) + (50*3)

    def test_create_meal_missing_name(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 1}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "name" in body["error"].lower()

    def test_create_meal_empty_ingredients(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Empty Meal",
                "ingredients": []
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "ingredient" in body["error"].lower()

    def test_create_meal_duplicate_ingredients(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Duplicate Test",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 1},
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 2}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "duplicate" in body["error"].lower()

    def test_create_meal_invalid_ingredient_id(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Test Meal",
                "ingredients": [
                    {"ingredient_id": "123e4567-e89b-12d3-a456-426614174000", "quantity": 1}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "invalid" in body["error"].lower()

    def test_create_meal_invalid_quantity(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Test Meal",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 0}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "quantity" in body["error"].lower()

    def test_create_meal_quantity_exceeds_max(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="POST",
            resource="/meals",
            body={
                "name": "Test Meal",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 20000}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "exceed" in body["error"].lower()


class TestListMeals:
    """Integration tests for GET /meals."""

    def test_list_meals_empty(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meals",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meals(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["meals"] == []

    def test_list_meals_with_data(
        self, mock_db_connection, mock_event_factory, test_user, test_meal
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meals",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meals(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["meals"]) == 1
        assert body["meals"][0]["name"] == "Test Meal"
        assert body["meals"][0]["total_calories"] == 200

    def test_list_meals_pagination(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient, db_connection
    ):
        # Create multiple meals
        cur = db_connection.cursor()
        for i in range(5):
            cur.execute(
                """
                INSERT INTO meals (user_id, name, total_calories)
                VALUES (%s, %s, %s)
                """,
                (test_user["id"], f"Meal {i}", 100 * i)
            )
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="GET",
            resource="/meals",
            query_params={"limit": "3", "offset": "1"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_meals(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["meals"]) == 3


class TestGetMeal:
    """Integration tests for GET /meals/{id}."""

    def test_get_meal_success(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, test_ingredient
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meals/{id}",
            path_params={"id": str(test_meal["id"])},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_meal(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "Test Meal"
        assert body["total_calories"] == 200
        assert len(body["ingredients"]) == 1
        assert body["ingredients"][0]["quantity"] == 2

    def test_get_meal_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meals/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_meal(event)

        assert response["statusCode"] == 404

    def test_get_meal_invalid_id(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/meals/{id}",
            path_params={"id": "invalid-uuid"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = get_meal(event)

        assert response["statusCode"] == 400


class TestUpdateMeal:
    """Integration tests for PUT /meals/{id}."""

    def test_update_meal_success(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, test_ingredient
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/meals/{id}",
            path_params={"id": str(test_meal["id"])},
            body={
                "name": "Updated Meal",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 3}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_meal(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "Updated Meal"
        assert body["total_calories"] == 300  # 100 * 3

    def test_update_meal_not_found(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/meals/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            body={
                "name": "Updated",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 1}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_meal(event)

        assert response["statusCode"] == 404

    def test_update_meal_duplicate_ingredients(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, test_ingredient
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/meals/{id}",
            path_params={"id": str(test_meal["id"])},
            body={
                "name": "Updated Meal",
                "ingredients": [
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 1},
                    {"ingredient_id": str(test_ingredient["id"]), "quantity": 2}
                ]
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_meal(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "duplicate" in body["error"].lower()


class TestDeleteMeal:
    """Integration tests for DELETE /meals/{id}."""

    def test_delete_meal_success(
        self, mock_db_connection, mock_event_factory, test_user, db_connection
    ):
        # Create a meal to delete
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO meals (user_id, name, total_calories)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (test_user["id"], "To Delete", 100)
        )
        meal_id = cur.fetchone()[0]
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="DELETE",
            resource="/meals/{id}",
            path_params={"id": str(meal_id)},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal(event)

        assert response["statusCode"] == 204

        # Verify deletion
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM meals WHERE id = %s", (meal_id,))
        assert cur.fetchone() is None
        cur.close()

    def test_delete_meal_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/meals/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal(event)

        assert response["statusCode"] == 404

    def test_delete_meal_cascades_meal_ingredients(
        self, mock_db_connection, mock_event_factory, test_user, test_meal, test_ingredient, db_connection
    ):
        """Test that deleting a meal also removes its meal_ingredients."""
        meal_id = test_meal["id"]

        # Verify meal_ingredients exist before deletion
        cur = db_connection.cursor()
        cur.execute("SELECT COUNT(*) FROM meal_ingredients WHERE meal_id = %s", (meal_id,))
        assert cur.fetchone()[0] > 0

        event = mock_event_factory(
            method="DELETE",
            resource="/meals/{id}",
            path_params={"id": str(meal_id)},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_meal(event)
        assert response["statusCode"] == 204

        # Verify meal_ingredients are also deleted
        cur.execute("SELECT COUNT(*) FROM meal_ingredients WHERE meal_id = %s", (meal_id,))
        assert cur.fetchone()[0] == 0
        cur.close()
