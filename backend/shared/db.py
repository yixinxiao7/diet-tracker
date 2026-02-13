import json
import os
import time
import psycopg2
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Cached across Lambda invocations (warm starts)
_connection = None
_secret_cache = None


def _get_db_secret():
    global _secret_cache

    if _secret_cache:
        return _secret_cache

    secret_arn = os.environ["DB_SECRET_ARN"]

    client = boto3.client("secretsmanager")
    last_exc = None
    for attempt in range(3):
        try:
            response = client.get_secret_value(SecretId=secret_arn)
            _secret_cache = json.loads(response["SecretString"])
            return _secret_cache
        except (ClientError, BotoCoreError) as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
                continue
            raise

    raise last_exc


def _is_connection_healthy(conn):
    """Check if the connection is still valid by running a simple query."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return True
    except Exception:
        return False


def get_connection():
    global _connection

    # Check if existing connection is healthy
    if _connection and _connection.closed == 0:
        if _is_connection_healthy(_connection):
            return _connection
        # Connection is broken, close and recreate
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None

    secret = _get_db_secret()

    _connection = psycopg2.connect(
        host=secret["host"],
        user=secret["username"],
        password=secret["password"],
        port=secret.get("port", 5432),
        dbname=os.environ["DB_NAME"],
        connect_timeout=5,
        options="-c statement_timeout=30000"  # 30 second statement timeout
    )

    return _connection


def get_internal_user_id(conn, cognito_user_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE cognito_user_id = %s",
        (cognito_user_id,)
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None
