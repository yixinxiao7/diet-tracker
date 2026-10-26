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


def _install_fake_connect(monkeypatch, calls, healthy=True):
    class FakeHealthCursor:
        def execute(self, *args, **kwargs):
            if not healthy:
                raise Exception("connection lost")

        def close(self):
            pass

    class FakePsycopgConn:
        def __init__(self):
            self.closed = 0

        def cursor(self):
            return FakeHealthCursor()

        def close(self):
            self.closed = 1

    def fake_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return FakePsycopgConn()

    monkeypatch.setattr(db_module, "_connection", None)
    monkeypatch.setattr(db_module.psycopg2, "connect", fake_connect)


def test_get_connection_uses_database_url_and_caches(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls)

    conn1 = db_module.get_connection()
    conn2 = db_module.get_connection()

    assert conn1 is conn2
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ("postgresql://user:pass@pooler:6543/postgres",)
    # Transaction pooler does not honor startup options
    assert "options" not in kwargs


def test_get_connection_reconnects_when_unhealthy(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls, healthy=False)

    conn1 = db_module.get_connection()
    conn2 = db_module.get_connection()

    assert conn1 is not conn2
    assert len(calls) == 2


def test_get_connection_reconnects_when_closed(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler:6543/postgres")
    _install_fake_connect(monkeypatch, calls)

    conn1 = db_module.get_connection()
    conn1.close()
    conn2 = db_module.get_connection()

    assert conn1 is not conn2
    assert len(calls) == 2
