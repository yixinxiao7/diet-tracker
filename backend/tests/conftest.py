import copy
import pytest

class FakeCursor:
    def __init__(self, fetchone_values=None, fetchall_values=None, rowcount=0, raise_on_execute=None):
        self._fetchone_values = list(fetchone_values or [])
        self._fetchall_values = list(fetchall_values or [])
        self.rowcount = rowcount
        self.executed = []
        self.executemany_calls = []
        self.raise_on_execute = raise_on_execute

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self.raise_on_execute:
            raise self.raise_on_execute

    def executemany(self, query, params=None):
        self.executemany_calls.append((query, params))
        if self.raise_on_execute:
            raise self.raise_on_execute

    def fetchone(self):
        return self._fetchone_values.pop(0) if self._fetchone_values else None

    def fetchall(self):
        return self._fetchall_values.pop(0) if self._fetchall_values else []

    def close(self):
        return None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def mock_event():
    return {
        "httpMethod": "GET",
        "resource": "/meals",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "test-cognito-user-id",
                    "email": "test@example.com"
                }
            }
        }
    }


@pytest.fixture
def event_copy(mock_event):
    return copy.deepcopy(mock_event)


@pytest.fixture
def fake_cursor():
    return FakeCursor()


@pytest.fixture
def fake_connection(fake_cursor):
    return FakeConnection(fake_cursor)
