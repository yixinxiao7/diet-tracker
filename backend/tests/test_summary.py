from backend.lambdas.summary.summary import get_daily_summary, get_range_summary


def test_get_daily_summary_missing_date(event_copy):
    event_copy["queryStringParameters"] = {}
    resp = get_daily_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_daily_summary_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"date": "2024/01/02"}
    resp = get_daily_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_range_summary_missing_params(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024-01-01"}
    resp = get_range_summary(event_copy)
    assert resp["statusCode"] == 400


def test_get_range_summary_invalid_date(event_copy):
    event_copy["queryStringParameters"] = {"from": "2024-01-01", "to": "2024/01/02"}
    resp = get_range_summary(event_copy)
    assert resp["statusCode"] == 400
