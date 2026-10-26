import json
import logging
import time
from unittest.mock import patch

from backend.shared.logging import JSONFormatter
from backend.shared.metrics import (
    put_metric,
    put_count,
    put_latency,
    timer,
)


def _metric_records(caplog):
    return [r for r in caplog.records if r.name == "backend.shared.metrics"]


class TestMetrics:
    """Test suite for the log-only metrics module."""

    def test_put_metric_logs_structured_fields(self, caplog):
        """Test that put_metric emits a structured log line with the metric."""
        with caplog.at_level(logging.INFO, logger="backend.shared.metrics"):
            put_metric("TestMetric", 42.5, unit="Count", dimensions={"Type": "Test"})

        records = _metric_records(caplog)
        assert len(records) == 1
        fields = records[0].extra_fields
        assert fields["metric_namespace"] == "DietTracker"
        assert fields["metric_name"] == "TestMetric"
        assert fields["metric_value"] == 42.5
        assert fields["metric_unit"] == "Count"
        assert fields["metric_dimensions"] == {"Type": "Test"}

    def test_put_metric_output_is_json(self, caplog):
        """Test that the metric log line formats as JSON with the metric fields."""
        with caplog.at_level(logging.INFO, logger="backend.shared.metrics"):
            put_metric("JsonMetric", 1, unit="Count")

        payload = json.loads(JSONFormatter().format(_metric_records(caplog)[-1]))
        assert payload["message"] == "metric"
        assert payload["metric_name"] == "JsonMetric"

    def test_put_metric_handles_exception(self):
        """Test that put_metric silently handles exceptions."""
        with patch("backend.shared.metrics.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("logging error")

            # This should not raise an exception
            put_metric("FailingMetric", 100)

    def test_put_count_convenience(self):
        """Test that put_count is a convenience wrapper for count=1."""
        with patch("backend.shared.metrics.put_metric") as mock_put_metric:
            put_count("MyCount", dimensions={"Source": "API"})

            mock_put_metric.assert_called_once_with(
                "MyCount",
                1,
                unit="Count",
                dimensions={"Source": "API"},
            )

    def test_put_latency_convenience(self):
        """Test that put_latency is a convenience wrapper for milliseconds."""
        with patch("backend.shared.metrics.put_metric") as mock_put_metric:
            put_latency("RequestTime", 123.45, dimensions={"Endpoint": "/api/users"})

            mock_put_metric.assert_called_once_with(
                "RequestTime",
                123.45,
                unit="Milliseconds",
                dimensions={"Endpoint": "/api/users"},
            )

    def test_timer_context_manager_measures_time(self):
        """Test that timer context manager measures elapsed time correctly."""
        with patch("backend.shared.metrics.put_latency") as mock_put_latency:
            with timer("TestOperation"):
                time.sleep(0.05)  # Sleep for 50ms

            mock_put_latency.assert_called_once()
            call_args = mock_put_latency.call_args

            # Verify metric name and dimensions
            assert call_args[0][0] == "TestOperation"

            # Verify elapsed time is approximately 50ms (with some tolerance)
            elapsed_ms = call_args[0][1]
            assert 40 < elapsed_ms < 150  # Allow 40-150ms due to timing variance

    def test_timer_publishes_metric(self):
        """Test that timer publishes the metric with dimensions."""
        with patch("backend.shared.metrics.put_latency") as mock_put_latency:
            dimensions = {"Operation": "Database", "Query": "SELECT"}
            with timer("DatabaseQuery", dimensions=dimensions):
                pass

            mock_put_latency.assert_called_once()
            call_args = mock_put_latency.call_args

            assert call_args[0][0] == "DatabaseQuery"
            assert call_args.kwargs["dimensions"] == dimensions

    def test_timer_exception_still_publishes(self):
        """Test that timer publishes metric even if an exception occurs."""
        with patch("backend.shared.metrics.put_latency") as mock_put_latency:
            try:
                with timer("FailingOperation"):
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Metric should still be published
            mock_put_latency.assert_called_once()

    def test_put_metric_without_dimensions(self, caplog):
        """Test that put_metric works without dimensions and defaults the unit."""
        with caplog.at_level(logging.INFO, logger="backend.shared.metrics"):
            put_metric("SimpleMetric", 100)

        fields = _metric_records(caplog)[-1].extra_fields
        assert fields["metric_name"] == "SimpleMetric"
        assert fields["metric_value"] == 100
        assert fields["metric_unit"] == "None"
        assert "metric_dimensions" not in fields
