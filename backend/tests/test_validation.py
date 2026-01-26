from backend.shared.validation import is_valid_date, is_valid_uuid


def test_is_valid_uuid():
    assert is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
    assert not is_valid_uuid("not-a-uuid")


def test_is_valid_date():
    assert is_valid_date("2024-01-02")
    assert not is_valid_date("01-02-2024")
