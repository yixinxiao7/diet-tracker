"""
Log-only custom metrics for the DietTracker application.

Each metric is emitted as a structured JSON log line (see shared/logging.py),
which lands in the platform's function logs.
Namespace: DietTracker
"""
import time
from contextlib import contextmanager
from typing import Optional, Dict

from backend.shared.logging import get_logger

NAMESPACE = "DietTracker"

logger = get_logger(__name__)


def put_metric(
    metric_name: str,
    value: float,
    unit: str = "None",
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """
    Emit a single metric as a structured log line under the DietTracker namespace.

    Args:
        metric_name: Name of the metric
        value: Numeric value of the metric
        unit: Unit (e.g., "Count", "Milliseconds", "None"). Default: "None"
        dimensions: Optional dict of dimension names to values

    Silently handles exceptions to ensure metrics never crash the app.
    """
    try:
        fields = {
            "metric_namespace": NAMESPACE,
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
        }

        if dimensions:
            fields["metric_dimensions"] = {k: str(v) for k, v in dimensions.items()}

        logger.info("metric", extra=fields)
    except Exception:
        # Silently fail - metrics should never crash the application
        pass


def put_count(metric_name: str, dimensions: Optional[Dict[str, str]] = None) -> None:
    """
    Convenience function to emit a count metric (value=1, unit=Count).

    Args:
        metric_name: Name of the metric
        dimensions: Optional dict of dimension names to values
    """
    put_metric(metric_name, 1, unit="Count", dimensions=dimensions)


def put_latency(
    metric_name: str,
    milliseconds: float,
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """
    Convenience function to emit a latency metric.

    Args:
        metric_name: Name of the metric
        milliseconds: Latency in milliseconds
        dimensions: Optional dict of dimension names to values
    """
    put_metric(metric_name, milliseconds, unit="Milliseconds", dimensions=dimensions)


@contextmanager
def timer(metric_name: str, dimensions: Optional[Dict[str, str]] = None):
    """
    Context manager that measures elapsed time and emits it as a metric.

    Args:
        metric_name: Name of the metric to emit
        dimensions: Optional dict of dimension names to values

    Usage:
        with timer("MyOperation", dimensions={"type": "compute"}):
            # do work
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        put_latency(metric_name, elapsed_ms, dimensions=dimensions)
