from datetime import datetime

from backend.lambdas.users import users as users_module
from backend.tests.conftest import FakeConnection, FakeCursor


def test_bootstrap_user_returns_ok(event_copy, monkeypatch):
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: conn)

    resp = users_module.bootstrap_user(event_copy)

    assert resp["statusCode"] == 200
    assert conn.committed is True
    assert conn.closed is True


def test_get_current_user_not_found(event_copy, monkeypatch):
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: conn)

    resp = users_module.get_current_user(event_copy)

    assert resp["statusCode"] == 404
    assert conn.closed is True


def test_get_current_user_success(event_copy, monkeypatch):
    row = (1, "test@example.com", datetime(2024, 1, 2, 3, 4, 5))
    cursor = FakeCursor(fetchone_values=[row])
    conn = FakeConnection(cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: conn)

    resp = users_module.get_current_user(event_copy)

    assert resp["statusCode"] == 200
    assert resp["body"] is not None
    assert conn.closed is True
