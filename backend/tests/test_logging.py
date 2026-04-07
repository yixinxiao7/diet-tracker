import json
import logging
from io import StringIO

from backend.shared.logging import get_logger, JSONFormatter


def test_get_logger_returns_logger():
    logger = get_logger("backend.test_logging")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "backend.test_logging"


def test_get_logger_default_level():
    logger = get_logger("backend.test_logging.level")
    assert logger.level == logging.INFO


def test_get_logger_has_handler():
    logger = get_logger("backend.test_logging.handler")
    assert len(logger.handlers) > 0


def test_get_logger_single_handler():
    logger = get_logger("backend.test_logging.single")
    handlers_before = len(logger.handlers)
    logger_again = get_logger("backend.test_logging.single")
    assert logger_again is logger
    assert len(logger_again.handlers) == handlers_before


def test_json_formatter_basic_message():
    """Test that JSONFormatter outputs valid JSON with required fields."""
    # Create a logger with a StringIO handler to capture output
    logger = logging.getLogger("test.json.basic")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Log a message
    logger.info("Test message")

    # Parse the JSON output
    output = stream.getvalue().strip()
    log_record = json.loads(output)

    # Verify required fields
    assert log_record["message"] == "Test message"
    assert log_record["level"] == "INFO"
    assert log_record["logger"] == "test.json.basic"
    assert "timestamp" in log_record
    assert "function" in log_record
    assert "line" in log_record


def test_json_formatter_with_extra_fields():
    """Test that JSONFormatter includes extra fields in JSON output."""
    logger = logging.getLogger("test.json.extra")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Log with extra fields using the custom logger behavior
    # We need to use the logger in a way that passes extra_fields through
    record = logging.LogRecord(
        name="test.json.extra",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test with extra",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {"user_id": "test-123", "request_id": "req-456"}

    # Format and verify
    formatted = handler.formatter.format(record)
    log_record = json.loads(formatted)

    assert log_record["message"] == "Test with extra"
    assert log_record["user_id"] == "test-123"
    assert log_record["request_id"] == "req-456"


def test_log_level_from_env(monkeypatch):
    """Test that LOG_LEVEL environment variable is respected."""
    # Set LOG_LEVEL to DEBUG in environment
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # We need to reload the module to pick up the new env var
    import importlib
    import backend.shared.logging as logging_module
    importlib.reload(logging_module)

    logger = logging_module.get_logger("test.log_level.debug")
    assert logger.level == logging.DEBUG

    # Reset for other tests
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    importlib.reload(logging_module)
