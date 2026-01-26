from backend.shared.auth import get_user_id, get_user_email
from backend.shared.db import get_connection
from backend.shared.logging import get_logger
from backend.shared.response import response

logger = get_logger(__name__)


def bootstrap_user(event):
    """
    POST /users/bootstrap

    Creates a user record if it does not already exist.
    This endpoint is idempotent.
    """
    cognito_user_id = get_user_id(event)
    email = get_user_email(event)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO users (cognito_user_id, email)
        VALUES (%s, %s)
        ON CONFLICT (cognito_user_id) DO NOTHING
    """
    cur.execute(query, (cognito_user_id, email))
    conn.commit()

    cur.close()
    conn.close()

    logger.info("Bootstrapped user", extra={"user_id": cognito_user_id})
    return response(200, {
        "message": "User bootstrap completed"
    })


def get_current_user(event):
    """
    GET /users/me
    """
    cognito_user_id = get_user_id(event)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, email, created_at
        FROM users
        WHERE cognito_user_id = %s
    """
    cur.execute(query, (cognito_user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return response(404, {"error": "User not found"})

    logger.info("Fetched current user", extra={"user_id": cognito_user_id})
    return response(200, {
        "id": row[0],
        "email": row[1],
        "created_at": row[2].isoformat()
    })
