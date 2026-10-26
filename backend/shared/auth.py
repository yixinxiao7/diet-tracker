import os

import jwt

SUPABASE_AUDIENCE = "authenticated"
SUPABASE_ALGORITHMS = ["RS256", "ES256"]

# Cached across warm serverless invocations; PyJWKClient caches fetched keys
_jwks_client = None


class AuthError(Exception):
    pass


def _supabase_url():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise AuthError("SUPABASE_URL is not configured")
    return url.rstrip("/")


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"{_supabase_url()}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def verify_token(token):
    """
    Verify a Supabase access token against the project's JWKS and return
    the claims the handlers read (sub, email). Raises AuthError on failure.
    """
    if not token:
        raise AuthError("Missing token")
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=SUPABASE_ALGORITHMS,
            audience=SUPABASE_AUDIENCE,
            issuer=f"{_supabase_url()}/auth/v1",
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(str(exc)) from exc
    return {"sub": payload["sub"], "email": payload.get("email")}


def get_claims(event):
    return event["requestContext"]["authorizer"]["claims"]


def get_auth_sub(event):
    return get_claims(event)["sub"]


def get_email(event):
    return get_claims(event).get("email")


def get_user_id(event):
    return get_auth_sub(event)


def get_user_email(event):
    return get_email(event)
