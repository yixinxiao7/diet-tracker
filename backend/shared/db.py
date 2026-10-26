import os
import psycopg2

# Cached across warm serverless invocations
_connection = None


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

    # Supabase transaction pooler (port 6543) does not honor startup options
    # such as statement_timeout, so none are passed here.
    _connection = psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
    )

    return _connection


def get_internal_user_id(conn, auth_user_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE auth_user_id = %s",
        (auth_user_id,)
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None
