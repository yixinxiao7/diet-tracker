import psycopg2

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
    try:
        query = """
            INSERT INTO users (cognito_user_id, email)
            VALUES (%s, %s)
            ON CONFLICT (cognito_user_id) DO NOTHING
        """
        cur.execute(query, (cognito_user_id, email))
        conn.commit()

        logger.info("Bootstrapped user", extra={"user_id": cognito_user_id})
        return response(200, {
            "message": "User bootstrap completed"
        })
    except psycopg2.IntegrityError:
        conn.rollback()
        logger.warning("User bootstrap conflict", extra={"user_id": cognito_user_id})
        return response(409, {"error": "User already exists"})
    except Exception:
        conn.rollback()
        logger.exception("Failed to bootstrap user", extra={"user_id": cognito_user_id})
        return response(500, {"error": "Failed to bootstrap user"})
    finally:
        cur.close()
        conn.close()


def get_current_user(event):
    """
    GET /users/me
    """
    cognito_user_id = get_user_id(event)

    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT id, email, created_at
            FROM users
            WHERE cognito_user_id = %s
        """
        cur.execute(query, (cognito_user_id,))
        row = cur.fetchone()

        if not row:
            return response(404, {"error": "User not found"})

        logger.info("Fetched current user", extra={"user_id": cognito_user_id})
        return response(200, {
            "id": row[0],
            "email": row[1],
            "created_at": row[2].isoformat()
        })
    except Exception:
        logger.exception("Failed to fetch current user", extra={"user_id": cognito_user_id})
        return response(500, {"error": "Failed to fetch current user"})
    finally:
        cur.close()
        conn.close()
