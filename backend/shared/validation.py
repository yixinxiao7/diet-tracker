import re
from datetime import datetime

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# Validation limits
MAX_NAME_LENGTH = 255
MAX_UNIT_LENGTH = 50
MAX_CALORIES = 100000  # 100k calories per unit is extremely high
MAX_QUANTITY = 10000   # Max quantity per ingredient or meal log


def is_valid_uuid(value):
    return bool(value and UUID_PATTERN.match(value))


def is_valid_date(value):
    if not value or not isinstance(value, str):
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_path_param(event, param_name):
    """Safely extract a path parameter from the event."""
    path_params = event.get("pathParameters")
    if not path_params:
        return None
    return path_params.get(param_name)


def validate_string_length(value, max_length, field_name):
    """Validate string is not empty and within max length. Returns error message or None."""
    if not value or not isinstance(value, str):
        return f"{field_name} is required"
    if len(value) > max_length:
        return f"{field_name} must be {max_length} characters or less"
    return None


def validate_calories(value):
    """Validate calories is a non-negative integer within bounds. Returns error message or None."""
    if value is None:
        return "calories_per_unit is required"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "calories_per_unit must be a number"
    if value < 0:
        return "calories_per_unit cannot be negative"
    if value > MAX_CALORIES:
        return f"calories_per_unit cannot exceed {MAX_CALORIES}"
    return None


def validate_quantity(value, field_name="quantity"):
    """Validate quantity is a positive number within bounds. Returns error message or None."""
    if value is None:
        return f"{field_name} is required"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{field_name} must be a number"
    if value <= 0:
        return f"{field_name} must be greater than 0"
    if value > MAX_QUANTITY:
        return f"{field_name} cannot exceed {MAX_QUANTITY}"
    return None


def validate_int_quantity(value, field_name="quantity"):
    """Validate quantity is a positive integer within bounds. Returns error message or None."""
    if value is None:
        return f"{field_name} is required"
    if isinstance(value, bool) or not isinstance(value, int):
        return f"{field_name} must be an integer"
    if value <= 0:
        return f"{field_name} must be greater than 0"
    if value > MAX_QUANTITY:
        return f"{field_name} cannot exceed {MAX_QUANTITY}"
    return None
