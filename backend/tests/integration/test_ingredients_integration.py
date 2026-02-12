"""Integration tests for ingredients endpoints."""
import json
import pytest

from backend.lambdas.meals.ingredients import (
    create_ingredient,
    list_ingredients,
    update_ingredient,
    delete_ingredient,
)


class TestCreateIngredient:
    """Integration tests for POST /ingredients."""

    def test_create_ingredient_success(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "name": "Chicken Breast",
                "calories_per_unit": 165,
                "unit": "100g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["name"] == "Chicken Breast"
        assert body["calories_per_unit"] == 165
        assert body["unit"] == "100g"
        assert "id" in body

    def test_create_ingredient_missing_name(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "calories_per_unit": 165,
                "unit": "100g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "name" in body["error"].lower()

    def test_create_ingredient_negative_calories(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "name": "Invalid Food",
                "calories_per_unit": -100,
                "unit": "g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "negative" in body["error"].lower()

    def test_create_ingredient_exceeds_max_calories(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "name": "High Cal Food",
                "calories_per_unit": 200000,
                "unit": "g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "exceed" in body["error"].lower()

    def test_create_ingredient_name_too_long(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "name": "A" * 300,
                "calories_per_unit": 100,
                "unit": "g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "255" in body["error"]

    def test_create_ingredient_user_not_found(
        self, mock_db_connection, mock_event_factory
    ):
        event = mock_event_factory(
            method="POST",
            resource="/ingredients",
            body={
                "name": "Test",
                "calories_per_unit": 100,
                "unit": "g"
            },
            cognito_user_id="non-existent-user"
        )

        response = create_ingredient(event)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "user" in body["error"].lower()


class TestListIngredients:
    """Integration tests for GET /ingredients."""

    def test_list_ingredients_empty(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/ingredients",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_ingredients(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["ingredients"] == []

    def test_list_ingredients_with_data(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="GET",
            resource="/ingredients",
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_ingredients(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["ingredients"]) == 1
        assert body["ingredients"][0]["name"] == "Test Ingredient"

    def test_list_ingredients_pagination(
        self, mock_db_connection, mock_event_factory, test_user, db_connection
    ):
        # Create multiple ingredients
        cur = db_connection.cursor()
        for i in range(5):
            cur.execute(
                """
                INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
                VALUES (%s, %s, %s, %s)
                """,
                (test_user["id"], f"Ingredient {i}", 100 + i, "g")
            )
        db_connection.commit()
        cur.close()

        # Test with limit
        event = mock_event_factory(
            method="GET",
            resource="/ingredients",
            query_params={"limit": "2"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_ingredients(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["ingredients"]) == 2

    def test_list_ingredients_invalid_pagination(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="GET",
            resource="/ingredients",
            query_params={"limit": "abc"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = list_ingredients(event)

        assert response["statusCode"] == 400


class TestUpdateIngredient:
    """Integration tests for PUT /ingredients/{id}."""

    def test_update_ingredient_success(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/ingredients/{id}",
            path_params={"id": str(test_ingredient["id"])},
            body={
                "name": "Updated Ingredient",
                "calories_per_unit": 150,
                "unit": "oz"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_ingredient(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "Updated Ingredient"
        assert body["calories_per_unit"] == 150
        assert body["unit"] == "oz"

    def test_update_ingredient_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/ingredients/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            body={
                "name": "Updated",
                "calories_per_unit": 100,
                "unit": "g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_ingredient(event)

        assert response["statusCode"] == 404

    def test_update_ingredient_invalid_id(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="PUT",
            resource="/ingredients/{id}",
            path_params={"id": "invalid-uuid"},
            body={
                "name": "Updated",
                "calories_per_unit": 100,
                "unit": "g"
            },
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = update_ingredient(event)

        assert response["statusCode"] == 400


class TestDeleteIngredient:
    """Integration tests for DELETE /ingredients/{id}."""

    def test_delete_ingredient_success(
        self, mock_db_connection, mock_event_factory, test_user, db_connection
    ):
        # Create an ingredient to delete
        cur = db_connection.cursor()
        cur.execute(
            """
            INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (test_user["id"], "To Delete", 100, "g")
        )
        ingredient_id = cur.fetchone()[0]
        db_connection.commit()
        cur.close()

        event = mock_event_factory(
            method="DELETE",
            resource="/ingredients/{id}",
            path_params={"id": str(ingredient_id)},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_ingredient(event)

        assert response["statusCode"] == 204

        # Verify deletion
        cur = db_connection.cursor()
        cur.execute("SELECT id FROM ingredients WHERE id = %s", (ingredient_id,))
        assert cur.fetchone() is None
        cur.close()

    def test_delete_ingredient_in_use_without_force(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient, test_meal
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/ingredients/{id}",
            path_params={"id": str(test_ingredient["id"])},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_ingredient(event)

        assert response["statusCode"] == 409
        body = json.loads(response["body"])
        assert "in use" in body["error"].lower()

    def test_delete_ingredient_in_use_with_force(
        self, mock_db_connection, mock_event_factory, test_user, test_ingredient, test_meal
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/ingredients/{id}",
            path_params={"id": str(test_ingredient["id"])},
            query_params={"force": "true"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_ingredient(event)

        assert response["statusCode"] == 204

    def test_delete_ingredient_not_found(
        self, mock_db_connection, mock_event_factory, test_user
    ):
        event = mock_event_factory(
            method="DELETE",
            resource="/ingredients/{id}",
            path_params={"id": "123e4567-e89b-12d3-a456-426614174000"},
            cognito_user_id=test_user["cognito_user_id"]
        )

        response = delete_ingredient(event)

        assert response["statusCode"] == 404
