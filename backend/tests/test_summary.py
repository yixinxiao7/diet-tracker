from datetime import date

from backend.lambdas.summary import summary as summary_module
from backend.tests.conftest import FakeConnection, FakeCursor


def test_get_daily_summary_missing_date(event_copy):
    event_copy["queryStringParameters"] = {}
    resp = summary_module.get_daily_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_daily_summary_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"date": "2024/01/02"}
    resp = summary_module.get_daily_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_range_summary_missing_params(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024-01-01"}
    resp = summary_module.get_range_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_range_summary_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024-01-01", "to": "2024/01/02"}
    resp = summary_module.get_range_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_daily_summary_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchone_values=[(450,)])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(summary_module, "get_connection", lambda: conn)
    monkeypatch.setattr(summary_module, "get_internal_user_id", lambda *_: 1)

    event_copy["queryStringParameters"] = {"date": "2024-01-02"}
    resp = summary_module.get_daily_summary(event_copy)
    assert resp["statusCode"] == 200


def test_get_range_summary_success(monkeypatch, event_copy):
    cursor = FakeCursor(fetchall_values=[[
        (date(2024, 1, 2), 450),
        (date(2024, 1, 3), 300)
    ]])
    conn = FakeConnection(cursor)

    monkeypatch.setattr(summary_module, "get_connection", lambda: conn)
    monkeypatch.setattr(summary_module, "get_internal_user_id", lambda *_: 1)

    event_copy["queryStringParameters"] = {"from": "2024-01-02", "to": "2024-01-03"}
    resp = summary_module.get_range_summary(event_copy)
    assert resp["statusCode"] == 200
