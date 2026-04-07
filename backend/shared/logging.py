import json
import logging
import os
import sys
from datetime import datetime

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON objects."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if provided
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger(logging.Logger):
    """Logger that supports extra fields for structured logging."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        # Extract extra fields from the extra dict
        if extra is None:
            extra = {}

        # Create a copy so we don't modify the original
        extra_copy = dict(extra)
        extra_copy_for_record = extra_copy.copy()

        # Pass extra_fields to the LogRecord
        if not hasattr(logging.LogRecord, "extra_fields"):
            logging.LogRecord.extra_fields = {}

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            extra={"extra_fields": extra_copy},
            stack_info=stack_info,
        )


def get_logger(name):
    """Get a logger instance with JSON structured logging."""
    # Set the logger class to our custom StructuredLogger
    logging.setLoggerClass(StructuredLogger)

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Only add handler if this logger doesn't already have one
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger
