import os
import psycopg2


def get_connection():
    """Open a new connection for one request; the caller must close it.

    Connections are not cached at module level: api/index.py runs handlers
    concurrently in a threadpool, and every handler closes its connection
    when done, so a shared connection would be closed out from under any
    request still using it. Supavisor (transaction pooler, port 6543) does
    the pooling, so a per-request connect is cheap.
    """
    # Supabase transaction pooler (port 6543) does not honor startup options
    # such as statement_timeout, so none are passed here.
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
    )


def get_internal_user_id(conn, auth_user_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE auth_user_id = %s",
        (auth_user_id,)
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None
