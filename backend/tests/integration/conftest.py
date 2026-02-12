"""
Integration test fixtures for diet-tracker backend.

These tests require a real PostgreSQL database. Set the following environment variables:
- INTEGRATION_TEST_DB_HOST (default: localhost)
- INTEGRATION_TEST_DB_PORT (default: 5432)
- INTEGRATION_TEST_DB_NAME (default: diet_tracker_test)
- INTEGRATION_TEST_DB_USER (default: postgres)
- INTEGRATION_TEST_DB_PASSWORD (default: postgres)

Run integration tests with: pytest backend/tests/integration -v
Skip if no database: tests are automatically skipped if connection fails.
"""
import os
import uuid
import copy
import json
import pytest
import psycopg2


def get_test_db_config():
    """Get test database configuration from environment variables."""
    return {
        "host": os.environ.get("INTEGRATION_TEST_DB_HOST", "localhost"),
        "port": int(os.environ.get("INTEGRATION_TEST_DB_PORT", 5432)),
        "dbname": os.environ.get("INTEGRATION_TEST_DB_NAME", "diet_tracker_test"),
        "user": os.environ.get("INTEGRATION_TEST_DB_USER", "postgres"),
        "password": os.environ.get("INTEGRATION_TEST_DB_PASSWORD", "postgres"),
    }


def can_connect_to_db():
    """Check if we can connect to the test database."""
    try:
        config = get_test_db_config()
        conn = psycopg2.connect(**config, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


# Skip all integration tests if database is not available
pytestmark = pytest.mark.skipif(
    not can_connect_to_db(),
    reason="Integration test database not available"
)


@pytest.fixture(scope="session")
def db_config():
    """Database configuration for tests."""
    return get_test_db_config()


@pytest.fixture(scope="session")
def setup_schema(db_config):
    """Create database schema once per test session."""
    conn = psycopg2.connect(**db_config)
    conn.autocommit = True
    cur = conn.cursor()

    # Read and execute schema
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "infra", "sql", "schema.sql"
    )
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    # Drop all tables first (in reverse order of dependencies)
    cur.execute("""
        DROP TABLE IF EXISTS meal_logs CASCADE;
        DROP TABLE IF EXISTS meal_ingredients CASCADE;
        DROP TABLE IF EXISTS meals CASCADE;
        DROP TABLE IF EXISTS ingredients CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)

    # Create schema
    cur.execute(schema_sql)

    cur.close()
    conn.close()
    yield
    # Cleanup after all tests
    conn = psycopg2.connect(**db_config)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        DROP TABLE IF EXISTS meal_logs CASCADE;
        DROP TABLE IF EXISTS meal_ingredients CASCADE;
        DROP TABLE IF EXISTS meals CASCADE;
        DROP TABLE IF EXISTS ingredients CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
    cur.close()
    conn.close()


@pytest.fixture
def db_connection(db_config, setup_schema):
    """Get a database connection for a test."""
    conn = psycopg2.connect(**db_config)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def clean_tables(db_connection):
    """Clean all tables before each test."""
    cur = db_connection.cursor()
    cur.execute("DELETE FROM meal_logs")
    cur.execute("DELETE FROM meal_ingredients")
    cur.execute("DELETE FROM meals")
    cur.execute("DELETE FROM ingredients")
    cur.execute("DELETE FROM users")
    db_connection.commit()
    cur.close()
    yield


@pytest.fixture
def test_user(db_connection, clean_tables):
    """Create a test user and return their IDs."""
    cur = db_connection.cursor()
    cognito_id = f"test-cognito-{uuid.uuid4()}"
    email = f"test-{uuid.uuid4()}@example.com"

    cur.execute(
        "INSERT INTO users (cognito_user_id, email) VALUES (%s, %s) RETURNING id",
        (cognito_id, email)
    )
    user_id = cur.fetchone()[0]
    db_connection.commit()
    cur.close()

    return {
        "id": user_id,
        "cognito_user_id": cognito_id,
        "email": email
    }


@pytest.fixture
def second_user(db_connection, clean_tables):
    """Create a second test user for authorization tests."""
    cur = db_connection.cursor()
    cognito_id = f"test-cognito-2-{uuid.uuid4()}"
    email = f"test-2-{uuid.uuid4()}@example.com"

    cur.execute(
        "INSERT INTO users (cognito_user_id, email) VALUES (%s, %s) RETURNING id",
        (cognito_id, email)
    )
    user_id = cur.fetchone()[0]
    db_connection.commit()
    cur.close()

    return {
        "id": user_id,
        "cognito_user_id": cognito_id,
        "email": email
    }


@pytest.fixture
def test_ingredient(db_connection, test_user):
    """Create a test ingredient."""
    cur = db_connection.cursor()
    cur.execute(
        """
        INSERT INTO ingredients (user_id, name, calories_per_unit, unit)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (test_user["id"], "Test Ingredient", 100, "g")
    )
    ingredient_id = cur.fetchone()[0]
    db_connection.commit()
    cur.close()

    return {
        "id": ingredient_id,
        "user_id": test_user["id"],
        "name": "Test Ingredient",
        "calories_per_unit": 100,
        "unit": "g"
    }


@pytest.fixture
def test_meal(db_connection, test_user, test_ingredient):
    """Create a test meal with an ingredient."""
    cur = db_connection.cursor()
    cur.execute(
        """
        INSERT INTO meals (user_id, name, total_calories)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (test_user["id"], "Test Meal", 200)
    )
    meal_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO meal_ingredients (meal_id, ingredient_id, quantity)
        VALUES (%s, %s, %s)
        """,
        (meal_id, test_ingredient["id"], 2)
    )
    db_connection.commit()
    cur.close()

    return {
        "id": meal_id,
        "user_id": test_user["id"],
        "name": "Test Meal",
        "total_calories": 200
    }


@pytest.fixture
def mock_event_factory():
    """Factory for creating mock Lambda events."""
    def create_event(
        method="GET",
        resource="/",
        path_params=None,
        query_params=None,
        body=None,
        cognito_user_id="test-cognito-user"
    ):
        event = {
            "httpMethod": method,
            "resource": resource,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": cognito_user_id,
                        "email": "test@example.com"
                    }
                }
            }
        }
        return event
    return create_event


@pytest.fixture
def mock_db_connection(db_connection, monkeypatch):
    """Patch the db module to use our test connection."""
    from backend.shared import db as db_module

    # Reset cached connection
    monkeypatch.setattr(db_module, "_connection", None)
    monkeypatch.setattr(db_module, "_secret_cache", None)

    def get_test_connection():
        return db_connection

    monkeypatch.setattr(db_module, "get_connection", get_test_connection)
    return db_connection
