import json

from backend.shared import db as db_module
from backend.shared.db import get_internal_user_id


class FakeCursor:
    def __init__(self, row=None):
        self._row = row

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return self._row

    def close(self):
        return None


class FakeConnection:
    def __init__(self, row=None):
        self._row = row

    def cursor(self):
        return FakeCursor(self._row)


def test_get_internal_user_id_found():
    conn = FakeConnection(row=(123,))
    assert get_internal_user_id(conn, "cognito") == 123


def test_get_internal_user_id_missing():
    conn = FakeConnection(row=None)
    assert get_internal_user_id(conn, "cognito") is None


def test_get_db_secret_and_connection_cache(monkeypatch):
    calls = {"secret": 0, "connect": 0}

    class FakeBotoClient:
        def get_secret_value(self, SecretId=None):
            calls["secret"] += 1
            return {"SecretString": json.dumps({
                "host": "localhost",
                "username": "user",
                "password": "pass",
                "port": 5432
            })}

    class FakeHealthCursor:
        def execute(self, *args, **kwargs):
            pass

        def close(self):
            pass

    class FakePsycopgConn:
        def __init__(self):
            self.closed = 0

        def cursor(self):
            return FakeHealthCursor()

    def fake_connect(**kwargs):
        calls["connect"] += 1
        return FakePsycopgConn()

    monkeypatch.setenv("DB_SECRET_ARN", "arn:secret")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setattr(db_module, "_secret_cache", None)
    monkeypatch.setattr(db_module, "_connection", None)
    monkeypatch.setattr(db_module.boto3, "client", lambda *_: FakeBotoClient())
    monkeypatch.setattr(db_module.psycopg2, "connect", lambda **kwargs: fake_connect(**kwargs))

    conn1 = db_module.get_connection()
    conn2 = db_module.get_connection()

    assert conn1 is conn2
    assert calls["secret"] == 1
    assert calls["connect"] == 1
