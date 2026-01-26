from backend.shared.auth import get_user_id, get_user_email


def test_get_user_id(mock_event):
    assert get_user_id(mock_event) == "test-cognito-user-id"


def test_get_user_email(mock_event):
    assert get_user_email(mock_event) == "test@example.com"
