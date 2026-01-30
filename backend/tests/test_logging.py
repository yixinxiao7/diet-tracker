import logging

from backend.shared.logging import get_logger


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
