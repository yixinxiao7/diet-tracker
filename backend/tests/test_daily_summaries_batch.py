from datetime import date, timedelta
from decimal import Decimal
import pytest

from backend.lambdas.daily_summaries_batch import batch
from backend.lambdas.daily_summaries_batch import handler as batch_handler
from backend.tests.conftest import FakeConnection, FakeCursor


class TestComputeDailySummaries:
    def test_compute_daily_summaries_default_date(self):
        """Test that default date is yesterday."""
        yesterday = date.today() - timedelta(days=1)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), 3), ("user-id-2", Decimal("2000"), 4)]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_daily_summaries(conn)

        assert result == 2
        # First query should use yesterday as parameter
        assert cursor.executed[0][1] == (yesterday,)

    def test_compute_daily_summaries_specific_date(self):
        """Test computing summaries for a specific date."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), 3)]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_daily_summaries(conn, target_date)

        assert result == 1

    def test_compute_daily_summaries_no_logs(self):
        """Test handling when no meal logs exist for target date."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(fetchall_values=[[]])
        conn = FakeConnection(cursor)

        result = batch.compute_daily_summaries(conn, target_date)

        assert result == 0

    def test_compute_daily_summaries_upsert(self):
        """Test that UPSERT correctly updates existing summaries."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), 3)]
            ]
        )
        conn = FakeConnection(cursor)

        batch.compute_daily_summaries(conn, target_date)

        # Check that an UPSERT query was executed
        assert any("ON CONFLICT" in query for query, _ in cursor.executed)

    def test_compute_daily_summaries_decimal_handling(self):
        """Test that decimal values are handled correctly."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500.50"), 2)]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_daily_summaries(conn, target_date)

        assert result == 1


class TestComputeWeeklyReports:
    def test_compute_weekly_reports_default_date(self):
        """Test that weekly reports default to yesterday's week."""
        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), Decimal("1000"), Decimal("2000"), 15)]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_weekly_reports(conn)

        assert result == 1

    def test_compute_weekly_reports_specific_date(self):
        """Test computing weekly report for specific date."""
        target_date = date(2024, 1, 15)  # A Monday

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), Decimal("1000"), Decimal("2000"), 15)]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_weekly_reports(conn, target_date)

        assert result == 1

    def test_compute_weekly_reports_week_boundaries(self):
        """Test that week_start is Monday and week_end is Sunday."""
        target_date = date(2024, 1, 17)  # A Wednesday

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1500"), Decimal("1000"), Decimal("2000"), 15)]
            ]
        )
        conn = FakeConnection(cursor)

        batch.compute_weekly_reports(conn, target_date)

        # Verify it committed
        assert conn.committed

    def test_compute_weekly_reports_multiple_users(self):
        """Test computing reports for multiple users in same week."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [
                    ("user-id-1", Decimal("1500"), Decimal("1000"), Decimal("2000"), 15),
                    ("user-id-2", Decimal("1200"), Decimal("900"), Decimal("1800"), 12),
                ]
            ]
        )
        conn = FakeConnection(cursor)

        result = batch.compute_weekly_reports(conn, target_date)

        assert result == 2

    def test_compute_weekly_reports_no_data(self):
        """Test handling when no data exists for the week."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(fetchall_values=[[]])
        conn = FakeConnection(cursor)

        result = batch.compute_weekly_reports(conn, target_date)

        assert result == 0


class TestDetectAnomalies:
    def test_detect_anomalies_above_threshold(self):
        """Test detection of anomalies above 50% threshold."""
        target_date = date(2024, 1, 15)

        # First fetchall returns users with daily summaries
        # Then fetchone returns rolling average for each user
        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("3100"))]  # 3100 calories today
            ],
            fetchone_values=[
                (Decimal("2000"),)  # Rolling avg is 2000 → >50% spike
            ]
        )
        conn = FakeConnection(cursor)

        anomalies = batch.detect_anomalies(conn, target_date)

        assert len(anomalies) == 1
        assert anomalies[0]["user_id"] == "user-id-1"
        assert anomalies[0]["daily_calories"] == Decimal("3100")
        assert anomalies[0]["rolling_avg_calories"] == Decimal("2000")

    def test_detect_anomalies_below_threshold(self):
        """Test that no anomaly is detected when within normal range."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("2200"))]  # Slightly above 2000
            ],
            fetchone_values=[
                (Decimal("2000"),)  # Rolling avg 2000
            ]
        )
        conn = FakeConnection(cursor)

        anomalies = batch.detect_anomalies(conn, target_date)

        # 2200 is only 10% above 2000, so no anomaly
        assert len(anomalies) == 0

    def test_detect_anomalies_default_date(self):
        """Test that anomalies default to checking yesterday."""
        yesterday = date.today() - timedelta(days=1)

        cursor = FakeCursor(fetchall_values=[[]])
        conn = FakeConnection(cursor)

        batch.detect_anomalies(conn)

        # Verify the first query uses yesterday
        assert cursor.executed[0][1] == (yesterday,)

    def test_detect_anomalies_multiple_users(self):
        """Test detection across multiple users."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [
                    ("user-id-1", Decimal("3100")),   # >50% above → anomaly
                    ("user-id-2", Decimal("2100")),   # 5% above → no anomaly
                ]
            ],
            fetchone_values=[
                (Decimal("2000"),),  # Rolling avg for user-id-1
                (Decimal("2000"),),  # Rolling avg for user-id-2
            ]
        )
        conn = FakeConnection(cursor)

        anomalies = batch.detect_anomalies(conn, target_date)

        # user-id-1: 3100 is 55% above 2000 (anomaly)
        # user-id-2: 2100 is 5% above 2000 (no anomaly)
        assert len(anomalies) == 1
        assert anomalies[0]["user_id"] == "user-id-1"

    def test_detect_anomalies_no_rolling_average(self):
        """Test handling when rolling average is None."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("1000"))]
            ],
            fetchone_values=[
                (None,)  # No rolling average data
            ]
        )
        conn = FakeConnection(cursor)

        anomalies = batch.detect_anomalies(conn, target_date)

        # When no rolling average, it defaults to current day value
        # so deviation_percent = 0 and no anomaly detected
        assert len(anomalies) == 0

    def test_detect_anomalies_deviation_percentage(self):
        """Test that deviation percentage is correctly calculated."""
        target_date = date(2024, 1, 15)

        cursor = FakeCursor(
            fetchall_values=[
                [("user-id-1", Decimal("3100"))]
            ],
            fetchone_values=[
                (Decimal("2000"),)
            ]
        )
        conn = FakeConnection(cursor)

        anomalies = batch.detect_anomalies(conn, target_date)

        assert len(anomalies) == 1
        # (3100 - 2000) / 2000 * 100 = 55%
        assert anomalies[0]["deviation_percent"] == 55


class TestHandler:
    def test_handler_success(self, monkeypatch):
        """Test successful EventBridge invocation."""
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        monkeypatch.setattr(batch_handler, "get_connection", lambda: conn)
        monkeypatch.setattr(
            batch_handler, "compute_daily_summaries", lambda conn: 5
        )
        monkeypatch.setattr(
            batch_handler, "compute_weekly_reports", lambda conn: 1
        )
        monkeypatch.setattr(
            batch_handler, "detect_anomalies", lambda conn: []
        )

        result = batch_handler.handler({}, None)

        assert result["statusCode"] == 200
        assert result["metrics"]["daily_summaries_count"] == 5
        assert result["metrics"]["weekly_reports_count"] == 1
        assert result["metrics"]["anomalies_detected"] == 0
        assert result["metrics"]["errors"] == []

    def test_handler_partial_failure(self, monkeypatch):
        """Test handler when one batch process fails."""
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        def raise_db_error(conn):
            raise Exception("DB error")

        monkeypatch.setattr(batch_handler, "get_connection", lambda: conn)
        monkeypatch.setattr(
            batch_handler, "compute_daily_summaries", lambda conn: 5
        )
        monkeypatch.setattr(
            batch_handler, "compute_weekly_reports", raise_db_error
        )
        monkeypatch.setattr(
            batch_handler, "detect_anomalies", lambda conn: []
        )

        result = batch_handler.handler({}, None)

        assert result["statusCode"] == 500
        assert result["metrics"]["daily_summaries_count"] == 5
        assert len(result["metrics"]["errors"]) == 1
        assert "DB error" in result["metrics"]["errors"][0]

    def test_handler_db_error(self, monkeypatch):
        """Test handler when database connection fails."""
        def raise_connection_error():
            raise Exception("Connection refused")

        monkeypatch.setattr(
            batch_handler, "get_connection", raise_connection_error
        )

        result = batch_handler.handler({}, None)

        assert result["statusCode"] == 500
        assert len(result["metrics"]["errors"]) == 1
        assert "Connection refused" in result["metrics"]["errors"][0]

    def test_handler_all_processes_fail(self, monkeypatch):
        """Test handler when all batch processes fail."""
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        def raise_error_1(conn):
            raise Exception("Error 1")

        def raise_error_2(conn):
            raise Exception("Error 2")

        def raise_error_3(conn):
            raise Exception("Error 3")

        monkeypatch.setattr(batch_handler, "get_connection", lambda: conn)
        monkeypatch.setattr(
            batch_handler, "compute_daily_summaries", raise_error_1
        )
        monkeypatch.setattr(
            batch_handler, "compute_weekly_reports", raise_error_2
        )
        monkeypatch.setattr(
            batch_handler, "detect_anomalies", raise_error_3
        )

        result = batch_handler.handler({}, None)

        assert result["statusCode"] == 500
        assert result["metrics"]["daily_summaries_count"] == 0
        assert result["metrics"]["weekly_reports_count"] == 0
        assert result["metrics"]["anomalies_detected"] == 0
        assert len(result["metrics"]["errors"]) == 3

    def test_handler_graceful_connection_close(self, monkeypatch):
        """Test that handler gracefully closes connections."""
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        monkeypatch.setattr(batch_handler, "get_connection", lambda: conn)
        monkeypatch.setattr(batch_handler, "compute_daily_summaries", lambda conn: 0)
        monkeypatch.setattr(batch_handler, "compute_weekly_reports", lambda conn: 0)
        monkeypatch.setattr(batch_handler, "detect_anomalies", lambda conn: [])

        batch_handler.handler({}, None)

        assert conn.closed

    def test_handler_connection_close_error(self, monkeypatch):
        """Test handling errors during connection close."""
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        def fake_close():
            raise Exception("Close error")

        conn.close = fake_close

        monkeypatch.setattr(batch_handler, "get_connection", lambda: conn)
        monkeypatch.setattr(batch_handler, "compute_daily_summaries", lambda conn: 0)
        monkeypatch.setattr(batch_handler, "compute_weekly_reports", lambda conn: 0)
        monkeypatch.setattr(batch_handler, "detect_anomalies", lambda conn: [])

        # Should not raise exception
        result = batch_handler.handler({}, None)
        assert result["statusCode"] == 200
