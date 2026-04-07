from backend.shared.db import get_connection
from backend.shared.logging import get_logger
from backend.lambdas.daily_summaries_batch.batch import (
    compute_daily_summaries,
    compute_weekly_reports,
    detect_anomalies
)

logger = get_logger(__name__)


def handler(event, context):
    """
    EventBridge scheduled invocation handler.

    Processes daily batch computations:
    1. Compute daily summaries
    2. Compute weekly reports
    3. Detect calorie anomalies

    Returns:
        {
            "statusCode": 200 or 500,
            "metrics": {
                "daily_summaries_count": int,
                "weekly_reports_count": int,
                "anomalies_detected": int,
                "errors": []
            }
        }
    """
    metrics = {
        "daily_summaries_count": 0,
        "weekly_reports_count": 0,
        "anomalies_detected": 0,
        "errors": []
    }

    conn = None
    try:
        conn = get_connection()

        # Compute daily summaries
        try:
            daily_count = compute_daily_summaries(conn)
            metrics["daily_summaries_count"] = daily_count
            logger.info("Successfully computed daily summaries", extra={"count": daily_count})
        except Exception as e:
            error_msg = f"Failed to compute daily summaries: {str(e)}"
            logger.error(error_msg)
            metrics["errors"].append(error_msg)

        # Compute weekly reports
        try:
            weekly_count = compute_weekly_reports(conn)
            metrics["weekly_reports_count"] = weekly_count
            logger.info("Successfully computed weekly reports", extra={"count": weekly_count})
        except Exception as e:
            error_msg = f"Failed to compute weekly reports: {str(e)}"
            logger.error(error_msg)
            metrics["errors"].append(error_msg)

        # Detect anomalies
        try:
            anomalies = detect_anomalies(conn)
            metrics["anomalies_detected"] = len(anomalies)
            logger.info("Successfully detected anomalies", extra={"count": len(anomalies)})
        except Exception as e:
            error_msg = f"Failed to detect anomalies: {str(e)}"
            logger.error(error_msg)
            metrics["errors"].append(error_msg)

        status_code = 200 if not metrics["errors"] else 500
        return {
            "statusCode": status_code,
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            "statusCode": 500,
            "metrics": {
                **metrics,
                "errors": metrics["errors"] + [f"Handler error: {str(e)}"]
            }
        }

    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")
