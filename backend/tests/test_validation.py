import pytest
from backend.shared.validation import is_valid_date, is_valid_uuid


class TestIsValidUuid:
    @pytest.mark.parametrize("value,expected", [
        ("123e4567-e89b-12d3-a456-426614174000", True),
        ("123E4567-E89B-12D3-A456-426614174000", True),
        ("00000000-0000-0000-0000-000000000000", True),
        ("ffffffff-ffff-ffff-ffff-ffffffffffff", True),
        ("not-a-uuid", False),
        ("", False),
        (None, False),
        ("123e4567-e89b-12d3-a456-42661417400", False),
        ("123e4567-e89b-12d3-a456-4266141740000", False),
        ("123e4567e89b12d3a456426614174000", False),
        ("123e4567-e89b-12d3-a456-42661417400g", False),
        ("123e4567-e89b-12d3-a456", False),
        (" 123e4567-e89b-12d3-a456-426614174000", False),
        ("123e4567-e89b-12d3-a456-426614174000 ", False),
    ])
    def test_is_valid_uuid(self, value, expected):
        assert is_valid_uuid(value) == expected


class TestIsValidDate:
    @pytest.mark.parametrize("value,expected", [
        ("2024-01-01", True),
        ("2024-12-31", True),
        ("2024-02-29", True),
        ("1999-01-01", True),
        ("2099-12-31", True),
        ("01-02-2024", False),
        ("2024/01/02", False),
        ("2024-13-01", False),
        ("2024-00-01", False),
        ("2024-01-32", False),
        ("2024-01-00", False),
        ("2023-02-29", False),
        ("2024-1-1", False),
        ("", False),
        (None, False),
        ("not-a-date", False),
        ("2024-01-01T00:00:00", False),
    ])
    def test_is_valid_date(self, value, expected):
        assert is_valid_date(value) == expected
