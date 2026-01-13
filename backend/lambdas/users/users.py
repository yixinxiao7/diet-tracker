from backend.shared.auth import get_user_id, get_user_email
from backend.shared.response import response
from backend.shared.db import get_connection


def bootstrap_user(event):
    """
    POST /users/bootstrap

    Creates a user record if it does not already exist.
    This endpoint is idempotent.
    """
    user_id = get_user_id(event)
    email = get_user_email(event)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO users (id, email)
        VALUES (%s, %s)
        ON CONFLICT (id) DO NOTHING
    """
    cur.execute(query, (user_id, email))
    conn.commit()

    cur.close()
    conn.close()

    return response(200, {
        "message": "User bootstrap completed"
    })


def get_current_user(event):
    """
    GET /users/me
    """
    user_id = get_user_id(event)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, email, created_at
        FROM users
        WHERE id = %s
    """
    cur.execute(query, (user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return response(404, {"error": "User not found"})

    return response(200, {
        "id": row[0],
        "email": row[1],
        "created_at": row[2].isoformat()
    })
