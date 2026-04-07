import pytest
import time
from unittest.mock import patch, MagicMock

from backend.shared.metrics import (
    put_metric,
    put_count,
    put_latency,
    timer,
)


class TestMetrics:
    """Test suite for CloudWatch metrics module."""

    def test_put_metric_success(self):
        """Test that put_metric successfully pushes a metric to CloudWatch."""
        with patch("backend.shared.metrics._cloudwatch_client") as mock_client:
            mock_cw = MagicMock()
            mock_client.return_value = mock_cw

            # Reset the global client
            import backend.shared.metrics as metrics_module
            metrics_module._cloudwatch_client = None

            with patch("boto3.client") as mock_boto_client:
                mock_boto_client.return_value = mock_cw

                put_metric("TestMetric", 42.5, unit="Count", dimensions={"Type": "Test"})

                # Verify put_metric_data was called with correct parameters
                mock_cw.put_metric_data.assert_called_once()
                call_args = mock_cw.put_metric_data.call_args

                assert call_args.kwargs["Namespace"] == "DietTracker"
                metric_data = call_args.kwargs["MetricData"][0]
                assert metric_data["MetricName"] == "TestMetric"
                assert metric_data["Value"] == 42.5
                assert metric_data["Unit"] == "Count"
                assert metric_data["Dimensions"] == [{"Name": "Type", "Value": "Test"}]

    def test_put_metric_handles_exception(self):
        """Test that put_metric silently handles exceptions."""
        with patch("boto3.client") as mock_boto_client:
            mock_cw = MagicMock()
            mock_cw.put_metric_data.side_effect = Exception("CloudWatch error")
            mock_boto_client.return_value = mock_cw

            # Reset the global client
            import backend.shared.metrics as metrics_module
            metrics_module._cloudwatch_client = None

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

    def test_put_metric_without_dimensions(self):
        """Test that put_metric works without dimensions."""
        with patch("boto3.client") as mock_boto_client:
            mock_cw = MagicMock()
            mock_boto_client.return_value = mock_cw

            # Reset the global client
            import backend.shared.metrics as metrics_module
            metrics_module._cloudwatch_client = None

            put_metric("SimpleMetric", 100)

            mock_cw.put_metric_data.assert_called_once()
            call_args = mock_cw.put_metric_data.call_args
            metric_data = call_args.kwargs["MetricData"][0]

            assert metric_data["MetricName"] == "SimpleMetric"
            assert metric_data["Value"] == 100
            assert metric_data["Unit"] == "None"
            assert "Dimensions" not in metric_data

    def test_put_metric_default_unit(self):
        """Test that put_metric uses 'None' as default unit."""
        with patch("boto3.client") as mock_boto_client:
            mock_cw = MagicMock()
            mock_boto_client.return_value = mock_cw

            # Reset the global client
            import backend.shared.metrics as metrics_module
            metrics_module._cloudwatch_client = None

            put_metric("MetricNoUnit", 42)

            mock_cw.put_metric_data.assert_called_once()
            call_args = mock_cw.put_metric_data.call_args
            metric_data = call_args.kwargs["MetricData"][0]

            assert metric_data["Unit"] == "None"
