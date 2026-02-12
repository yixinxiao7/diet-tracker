"""
Integration test fixtures for diet-tracker backend.

These tests use a mocked in-memory database that simulates PostgreSQL behavior,
allowing tests to run without requiring a real database instance.

Run integration tests with: pytest backend/tests/integration -v
"""
import uuid
import json
from datetime import date, datetime
import pytest


class MockCursor:
    """Mock cursor that simulates PostgreSQL cursor behavior."""

    def __init__(self, db):
        self._db = db
        self._results = []
        self._result_index = 0
        self.rowcount = 0

    def execute(self, query, params=None):
        self._results = []
        self._result_index = 0

        # Normalize query: collapse all whitespace and convert to uppercase
        query_normalized = " ".join(query.split()).upper()

        if query_normalized.strip() == "BEGIN":
            return

        if "SELECT 1" in query_normalized:
            self._results = [(1,)]
            return

        if query_normalized.startswith("INSERT"):
            self._handle_insert(query_normalized, params)
        elif query_normalized.startswith("SELECT"):
            self._handle_select(query_normalized, params)
        elif query_normalized.startswith("UPDATE"):
            self._handle_update(query_normalized, params)
        elif query_normalized.startswith("DELETE"):
            self._handle_delete(query_normalized, params)

    def _handle_insert(self, query_upper, params):
        if "INTO USERS" in query_upper:
            user_id = str(uuid.uuid4())
            self._db["users"][user_id] = {
                "id": user_id,
                "cognito_user_id": params[0],
                "email": params[1],
                "created_at": datetime.now()
            }
            self._results = [(user_id,)]
            self.rowcount = 1

        elif "INTO INGREDIENTS" in query_upper:
            ing_id = str(uuid.uuid4())
            self._db["ingredients"][ing_id] = {
                "id": ing_id,
                "user_id": str(params[0]),
                "name": params[1],
                "calories_per_unit": params[2],
                "unit": params[3]
            }
            self._results = [(ing_id,)]
            self.rowcount = 1

        elif "INTO MEALS" in query_upper and "MEAL_INGREDIENTS" not in query_upper:
            meal_id = str(uuid.uuid4())
            self._db["meals"][meal_id] = {
                "id": meal_id,
                "user_id": str(params[0]),
                "name": params[1],
                "total_calories": params[2] if len(params) > 2 else 0,
                "created_at": datetime.now()
            }
            self._results = [(meal_id,)]
            self.rowcount = 1

        elif "INTO MEAL_INGREDIENTS" in query_upper:
            mi_id = str(uuid.uuid4())
            self._db["meal_ingredients"][mi_id] = {
                "id": mi_id,
                "meal_id": str(params[0]),
                "ingredient_id": str(params[1]),
                "quantity": params[2]
            }
            self.rowcount = 1

        elif "INTO MEAL_LOGS" in query_upper:
            log_id = str(uuid.uuid4())
            log_date = params[2] if isinstance(params[2], date) else date.fromisoformat(params[2])
            self._db["meal_logs"][log_id] = {
                "id": log_id,
                "user_id": str(params[0]),
                "meal_id": str(params[1]),
                "date": log_date,
                "quantity": params[3] if len(params) > 3 else 1
            }
            self._results = [(log_id,)]
            self.rowcount = 1

    def _handle_select(self, query_upper, params):
        # Remove all spaces for easier pattern matching
        query_no_spaces = query_upper.replace(" ", "")

        if "FROM USERS" in query_upper and "COGNITO_USER_ID" in query_upper:
            cognito_id = params[0]
            for user in self._db["users"].values():
                if user["cognito_user_id"] == cognito_id:
                    self._results = [(user["id"],)]
                    return
            self._results = []

        elif "FROM INGREDIENTS" in query_upper and "ID = ANY" in query_upper:
            user_id = params[0]
            ingredient_ids = params[1]
            results = []
            for ing in self._db["ingredients"].values():
                if str(ing["user_id"]) == str(user_id) and str(ing["id"]) in [str(i) for i in ingredient_ids]:
                    results.append((ing["id"], ing["calories_per_unit"]))
            self._results = results

        elif "FROM INGREDIENTS" in query_upper and "WHEREID=%SANDUSER_ID=%S" in query_no_spaces:
            ing_id, user_id = params[0], params[1]
            for ing in self._db["ingredients"].values():
                if str(ing["id"]) == str(ing_id) and str(ing["user_id"]) == str(user_id):
                    self._results = [(ing["id"], ing["name"], ing["calories_per_unit"], ing["unit"])]
                    return
            self._results = []

        elif "FROM INGREDIENTS" in query_upper and "USER_ID" in query_upper:
            user_id = params[0]
            results = []
            for ing in self._db["ingredients"].values():
                if str(ing["user_id"]) == str(user_id):
                    results.append((ing["id"], ing["name"], ing["calories_per_unit"], ing["unit"]))
            limit = params[1] if len(params) >= 2 else 50
            offset = params[2] if len(params) >= 3 else 0
            self._results = results[offset:offset + limit]

        elif "FROM MEALS M" in query_upper and "LEFT JOIN MEAL_INGREDIENTS" in query_upper:
            meal_id, user_id = params[0], params[1]
            results = []
            for meal in self._db["meals"].values():
                if str(meal["id"]) == str(meal_id) and str(meal["user_id"]) == str(user_id):
                    has_ingredients = False
                    for mi in self._db["meal_ingredients"].values():
                        if str(mi["meal_id"]) == str(meal_id):
                            for ing in self._db["ingredients"].values():
                                if str(ing["id"]) == str(mi["ingredient_id"]):
                                    results.append((
                                        meal["id"], meal["name"], meal["total_calories"],
                                        meal["created_at"], mi["quantity"],
                                        ing["id"], ing["name"], ing["calories_per_unit"], ing["unit"]
                                    ))
                                    has_ingredients = True
                    if not has_ingredients:
                        results.append((
                            meal["id"], meal["name"], meal["total_calories"],
                            meal["created_at"], None, None, None, None, None
                        ))
                    break
            self._results = results

        # Check for meal existence: SELECT id FROM meals WHERE id = %s AND user_id = %s
        elif "SELECTIDFROMMEALS" in query_no_spaces and "WHEREID=%SANDUSER_ID=%S" in query_no_spaces:
            meal_id, user_id = params[0], params[1]
            for meal in self._db["meals"].values():
                if str(meal["id"]) == str(meal_id) and str(meal["user_id"]) == str(user_id):
                    self._results = [(meal["id"],)]
                    return
            self._results = []

        # List meals: SELECT ... FROM meals WHERE user_id = %s ORDER BY ...
        elif "FROMMEALS" in query_no_spaces and "WHEREUSER_ID=%S" in query_no_spaces and "ORDERBY" in query_no_spaces:
            user_id = params[0]
            results = []
            for meal in self._db["meals"].values():
                if str(meal["user_id"]) == str(user_id):
                    results.append((meal["id"], meal["name"], meal["total_calories"], meal["created_at"]))
            results.sort(key=lambda x: x[3], reverse=True)
            limit = params[1] if len(params) > 1 else 50
            offset = params[2] if len(params) > 2 else 0
            self._results = results[offset:offset + limit]

        # Daily summary: SELECT COALESCE(SUM(...)) FROM meal_logs ml JOIN meals m ... WHERE ml.date = %s
        elif "SUM(" in query_upper and "MEAL_LOGS" in query_upper and "ML.DATE=%S" in query_no_spaces:
            user_id, query_date = params[0], params[1]
            total = 0
            for log in self._db["meal_logs"].values():
                if str(log["user_id"]) == str(user_id):
                    log_date = log["date"].isoformat() if isinstance(log["date"], date) else log["date"]
                    if log_date == query_date:
                        for meal in self._db["meals"].values():
                            if str(meal["id"]) == str(log["meal_id"]):
                                total += int(meal["total_calories"]) * log["quantity"]
            self._results = [(total,)]

        # Range summary: SELECT ml.date, COALESCE(SUM(...)) FROM meal_logs ml JOIN meals m ... WHERE ... BETWEEN
        elif "SUM(" in query_upper and "MEAL_LOGS" in query_upper and "BETWEEN" in query_upper:
            user_id, date_from, date_to = params[0], params[1], params[2]
            daily_totals = {}
            for log in self._db["meal_logs"].values():
                if str(log["user_id"]) == str(user_id):
                    log_date = log["date"]
                    if isinstance(log_date, str):
                        log_date = date.fromisoformat(log_date)
                    if date.fromisoformat(date_from) <= log_date <= date.fromisoformat(date_to):
                        for meal in self._db["meals"].values():
                            if str(meal["id"]) == str(log["meal_id"]):
                                if log_date not in daily_totals:
                                    daily_totals[log_date] = 0
                                daily_totals[log_date] += int(meal["total_calories"]) * log["quantity"]
            # Return date objects, not strings
            self._results = [(d, t) for d, t in sorted(daily_totals.items())]

        # List meal logs: SELECT ml.id, ml.meal_id, ml.date, ... FROM meal_logs ml JOIN meals m
        elif "FROM MEAL_LOGS ML" in query_upper and "JOIN MEALS M" in query_upper:
            user_id = params[0]
            results = []
            for log in self._db["meal_logs"].values():
                if str(log["user_id"]) == str(user_id):
                    date_from = params[1] if len(params) > 1 and params[1] else None
                    date_to = params[3] if len(params) > 3 and params[3] else None

                    # Ensure log_date is a date object
                    log_date = log["date"]
                    if isinstance(log_date, str):
                        log_date = date.fromisoformat(log_date)

                    if date_from and log_date < date.fromisoformat(date_from):
                        continue
                    if date_to and log_date > date.fromisoformat(date_to):
                        continue

                    for meal in self._db["meals"].values():
                        if str(meal["id"]) == str(log["meal_id"]):
                            results.append((
                                log["id"], log["meal_id"], log_date,
                                log["quantity"], meal["name"], meal["total_calories"]
                            ))
                            break
            results.sort(key=lambda x: (x[2], str(x[0])), reverse=True)
            limit = params[5] if len(params) > 5 else 50
            offset = params[6] if len(params) > 6 else 0
            self._results = results[offset:offset + limit]

        elif "COUNT(*)" in query_upper and "FROM MEAL_INGREDIENTS MI" in query_upper:
            ingredient_id, user_id = params[0], params[1]
            count = 0
            for mi in self._db["meal_ingredients"].values():
                if str(mi["ingredient_id"]) == str(ingredient_id):
                    for ing in self._db["ingredients"].values():
                        if str(ing["id"]) == str(ingredient_id) and str(ing["user_id"]) == str(user_id):
                            count += 1
                            break
            self._results = [(count,)]

        # Count meal_ingredients for a meal: SELECT COUNT(*) FROM meal_ingredients WHERE meal_id = %s
        elif "COUNT(*)" in query_upper and "FROM MEAL_INGREDIENTS" in query_upper and "MEAL_ID" in query_upper:
            meal_id = params[0]
            count = sum(1 for mi in self._db["meal_ingredients"].values() if str(mi["meal_id"]) == str(meal_id))
            self._results = [(count,)]

    def _handle_update(self, query_upper, params):
        if "UPDATE INGREDIENTS" in query_upper:
            name, calories, unit, ing_id, user_id = params
            for ing in self._db["ingredients"].values():
                if str(ing["id"]) == str(ing_id) and str(ing["user_id"]) == str(user_id):
                    ing["name"] = name
                    ing["calories_per_unit"] = calories
                    ing["unit"] = unit
                    self._results = [(ing["id"],)]
                    self.rowcount = 1
                    return
            self.rowcount = 0

        elif "UPDATE MEALS" in query_upper:
            name, total_calories, meal_id, user_id = params
            for meal in self._db["meals"].values():
                if str(meal["id"]) == str(meal_id) and str(meal["user_id"]) == str(user_id):
                    meal["name"] = name
                    meal["total_calories"] = total_calories
                    self._results = [(meal["id"],)]
                    self.rowcount = 1
                    return
            self.rowcount = 0

    def _handle_delete(self, query_upper, params):
        if "FROM INGREDIENTS" in query_upper:
            ing_id, user_id = params
            to_delete = None
            for key, ing in self._db["ingredients"].items():
                if str(ing["id"]) == str(ing_id) and str(ing["user_id"]) == str(user_id):
                    to_delete = key
                    break
            if to_delete:
                del self._db["ingredients"][to_delete]
                mi_to_delete = [k for k, mi in self._db["meal_ingredients"].items()
                               if str(mi["ingredient_id"]) == str(ing_id)]
                for k in mi_to_delete:
                    del self._db["meal_ingredients"][k]
                self.rowcount = 1
            else:
                self.rowcount = 0

        elif "FROM MEAL_INGREDIENTS" in query_upper:
            meal_id = params[0]
            to_delete = [k for k, mi in self._db["meal_ingredients"].items()
                        if str(mi["meal_id"]) == str(meal_id)]
            for k in to_delete:
                del self._db["meal_ingredients"][k]
            self.rowcount = len(to_delete)

        elif "FROM MEALS" in query_upper:
            meal_id, user_id = params
            to_delete = None
            for key, meal in self._db["meals"].items():
                if str(meal["id"]) == str(meal_id) and str(meal["user_id"]) == str(user_id):
                    to_delete = key
                    break
            if to_delete:
                del self._db["meals"][to_delete]
                mi_to_delete = [k for k, mi in self._db["meal_ingredients"].items()
                               if str(mi["meal_id"]) == str(meal_id)]
                for k in mi_to_delete:
                    del self._db["meal_ingredients"][k]
                ml_to_delete = [k for k, ml in self._db["meal_logs"].items()
                               if str(ml["meal_id"]) == str(meal_id)]
                for k in ml_to_delete:
                    del self._db["meal_logs"][k]
                self.rowcount = 1
            else:
                self.rowcount = 0

        elif "FROM MEAL_LOGS" in query_upper:
            log_id, user_id = params
            to_delete = None
            for key, log in self._db["meal_logs"].items():
                if str(log["id"]) == str(log_id) and str(log["user_id"]) == str(user_id):
                    to_delete = key
                    break
            if to_delete:
                del self._db["meal_logs"][to_delete]
                self.rowcount = 1
            else:
                self.rowcount = 0

    def executemany(self, query, params_list):
        for params in params_list:
            self.execute(query, params)

    def fetchone(self):
        if self._result_index < len(self._results):
            result = self._results[self._result_index]
            self._result_index += 1
            return result
        return None

    def fetchall(self):
        results = self._results[self._result_index:]
        self._result_index = len(self._results)
        return results

    def close(self):
        pass


class MockConnection:
    """Mock connection that simulates PostgreSQL connection behavior."""

    def __init__(self, db):
        self._db = db
        self.closed = 0

    def cursor(self):
        return MockCursor(self._db)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = 1


@pytest.fixture
def mock_db():
    """Get a fresh mock database for each test."""
    return {
        "users": {},
        "ingredients": {},
        "meals": {},
        "meal_ingredients": {},
        "meal_logs": {}
    }


@pytest.fixture
def mock_db_connection(mock_db, monkeypatch):
    """Patch the db module to use our mock connection."""
    from backend.shared import db as db_module
    from backend.lambdas.meals import ingredients as ingredients_module
    from backend.lambdas.meals import meals as meals_module
    from backend.lambdas.meal_logs import meal_logs as meal_logs_module
    from backend.lambdas.summary import summary as summary_module

    conn = MockConnection(mock_db)

    def get_mock_connection():
        return conn

    # Patch at the source module
    monkeypatch.setattr(db_module, "_connection", None)
    monkeypatch.setattr(db_module, "_secret_cache", None)
    monkeypatch.setattr(db_module, "get_connection", get_mock_connection)

    # Patch at all import locations
    monkeypatch.setattr(ingredients_module, "get_connection", get_mock_connection)
    monkeypatch.setattr(meals_module, "get_connection", get_mock_connection)
    monkeypatch.setattr(meal_logs_module, "get_connection", get_mock_connection)
    monkeypatch.setattr(summary_module, "get_connection", get_mock_connection)

    return conn, mock_db


@pytest.fixture
def db_connection(mock_db_connection):
    """Provide direct access to mock_db for tests that manipulate data directly."""
    conn, mock_db = mock_db_connection
    # Return an object that provides both connection and db access
    class DbAccess:
        def __init__(self, conn, db):
            self._conn = conn
            self._db = db

        def cursor(self):
            return self._conn.cursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        @property
        def mock_db(self):
            return self._db

    return DbAccess(conn, mock_db)


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
        return {
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
    return create_event


@pytest.fixture
def test_user(mock_db_connection):
    """Create a test user and return their IDs."""
    conn, mock_db = mock_db_connection
    user_id = str(uuid.uuid4())
    cognito_id = f"test-cognito-{uuid.uuid4()}"
    email = f"test-{uuid.uuid4()}@example.com"

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


@pytest.fixture
def second_user(mock_db_connection):
    """Create a second test user for authorization tests."""
    conn, mock_db = mock_db_connection
    user_id = str(uuid.uuid4())
    cognito_id = f"test-cognito-2-{uuid.uuid4()}"
    email = f"test-2-{uuid.uuid4()}@example.com"

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


@pytest.fixture
def test_ingredient(mock_db_connection, test_user):
    """Create a test ingredient."""
    conn, mock_db = mock_db_connection
    ingredient_id = str(uuid.uuid4())

    mock_db["ingredients"][ingredient_id] = {
        "id": ingredient_id,
        "user_id": test_user["id"],
        "name": "Test Ingredient",
        "calories_per_unit": 100,
        "unit": "g"
    }

    return {
        "id": ingredient_id,
        "user_id": test_user["id"],
        "name": "Test Ingredient",
        "calories_per_unit": 100,
        "unit": "g"
    }


@pytest.fixture
def test_meal(mock_db_connection, test_user, test_ingredient):
    """Create a test meal with an ingredient."""
    conn, mock_db = mock_db_connection
    meal_id = str(uuid.uuid4())

    mock_db["meals"][meal_id] = {
        "id": meal_id,
        "user_id": test_user["id"],
        "name": "Test Meal",
        "total_calories": 200,
        "created_at": datetime.now()
    }

    mi_id = str(uuid.uuid4())
    mock_db["meal_ingredients"][mi_id] = {
        "id": mi_id,
        "meal_id": meal_id,
        "ingredient_id": test_ingredient["id"],
        "quantity": 2
    }

    return {
        "id": meal_id,
        "user_id": test_user["id"],
        "name": "Test Meal",
        "total_calories": 200
    }
