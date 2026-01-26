from datetime import datetime

from backend.lambdas.users import users as users_module


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

    def commit(self):
        return None

    def close(self):
        return None


def test_bootstrap_user_returns_ok(event_copy, monkeypatch):
    monkeypatch.setattr(users_module, "get_connection", lambda: FakeConnection())
    resp = users_module.bootstrap_user(event_copy)
    assert resp["statusCode"] == 200


def test_get_current_user_not_found(event_copy, monkeypatch):
    monkeypatch.setattr(users_module, "get_connection", lambda: FakeConnection())
    resp = users_module.get_current_user(event_copy)
    assert resp["statusCode"] == 404


def test_get_current_user_success(event_copy, monkeypatch):
    row = (1, "test@example.com", datetime(2024, 1, 2, 3, 4, 5))
    monkeypatch.setattr(users_module, "get_connection", lambda: FakeConnection(row=row))
    resp = users_module.get_current_user(event_copy)
    assert resp["statusCode"] == 200
    assert resp["body"] is not None
