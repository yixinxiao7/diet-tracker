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
    assert get_internal_user_id(conn, "auth-user") == 123


def test_get_internal_user_id_missing():
    conn = FakeConnection(row=None)
    assert get_internal_user_id(conn, "auth-user") is None


def _install_fake_connect(monkeypatch, calls):
    class FakePsycopgConn:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed = 1

    def fake_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return FakePsycopgConn()

    monkeypatch.setattr(db_module.psycopg2, "connect", fake_connect)


def test_get_connection_uses_database_url(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls)

    db_module.get_connection()

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ("postgresql://user:pass@pooler:6543/postgres",)
    # Transaction pooler does not honor startup options
    assert "options" not in kwargs


def test_get_connection_opens_a_new_connection_per_call(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls)

    conn1 = db_module.get_connection()
    conn1.close()
    conn2 = db_module.get_connection()

    assert conn1 is not conn2
    assert conn2.closed == 0
    assert len(calls) == 2


def test_concurrent_requests_do_not_share_a_connection(monkeypatch):
    # api/index.py runs handlers in a threadpool, so two requests on one warm
    # instance can interleave: A and B both get a connection, A finishes and
    # calls conn.close(), then B runs its query. B must not be holding A's
    # (now closed) connection.
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls)

    conn_a = db_module.get_connection()
    conn_b = db_module.get_connection()
    conn_a.close()

    assert conn_b.closed == 0
