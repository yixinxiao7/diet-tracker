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
