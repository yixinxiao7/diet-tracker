"""
CloudWatch custom metrics for the DietTracker application.
Namespace: DietTracker
"""
import time
from contextlib import contextmanager
from typing import Optional, Dict

_cloudwatch_client = None


def _get_cloudwatch_client():
    """Lazy-initialize CloudWatch client."""
    global _cloudwatch_client
    if _cloudwatch_client is None:
        try:
            import boto3
            _cloudwatch_client = boto3.client("cloudwatch")
        except Exception:
            # Silently fail if boto3 is not available or credentials are missing
            pass
    return _cloudwatch_client


def put_metric(
    metric_name: str,
    value: float,
    unit: str = "None",
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """
    Push a single metric to CloudWatch under the DietTracker namespace.

    Args:
        metric_name: Name of the metric
        value: Numeric value of the metric
        unit: CloudWatch unit (e.g., "Count", "Milliseconds", "None"). Default: "None"
        dimensions: Optional dict of dimension names to values

    Silently handles exceptions to ensure metrics never crash the app.
    """
    try:
        client = _get_cloudwatch_client()
        if client is None:
            return

        metric_data = {
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
        }

        if dimensions:
            metric_data["Dimensions"] = [
                {"Name": k, "Value": str(v)} for k, v in dimensions.items()
            ]

        client.put_metric_data(
            Namespace="DietTracker",
            MetricData=[metric_data],
        )
    except Exception:
        # Silently fail - metrics should never crash the application
        pass


def put_count(metric_name: str, dimensions: Optional[Dict[str, str]] = None) -> None:
    """
    Convenience function to push a count metric (value=1, unit=Count).

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
    Convenience function to push a latency metric.

    Args:
        metric_name: Name of the metric
        milliseconds: Latency in milliseconds
        dimensions: Optional dict of dimension names to values
    """
    put_metric(metric_name, milliseconds, unit="Milliseconds", dimensions=dimensions)


@contextmanager
def timer(metric_name: str, dimensions: Optional[Dict[str, str]] = None):
    """
    Context manager that measures elapsed time and publishes it as a metric.

    Args:
        metric_name: Name of the metric to publish
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
