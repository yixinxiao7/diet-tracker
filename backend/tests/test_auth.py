import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.shared import auth as auth_module
from backend.shared.auth import AuthError, get_user_id, get_user_email, verify_token
from backend.tests.conftest import SUPABASE_TEST_URL


def test_get_user_id(mock_event):
    assert get_user_id(mock_event) == "test-auth-user-id"


def test_get_user_email(mock_event):
    assert get_user_email(mock_event) == "test@example.com"


def test_verify_token_returns_sub_and_email(make_token):
    claims = verify_token(make_token())

    assert claims == {"sub": "test-auth-user-id", "email": "test@example.com"}


def test_verify_token_fetches_project_jwks(make_token):
    verify_token(make_token())

    assert make_token.jwks_requests == [f"{SUPABASE_TEST_URL}/auth/v1/.well-known/jwks.json"]


def test_verify_token_caches_jwks_client(make_token):
    verify_token(make_token())
    client = auth_module._jwks_client
    verify_token(make_token())

    assert auth_module._jwks_client is client
    assert len(make_token.jwks_requests) == 1


def test_verify_token_without_email(make_token):
    claims = verify_token(make_token(email=None))

    assert claims == {"sub": "test-auth-user-id", "email": None}


@pytest.mark.parametrize("overrides", [
    {"aud": "anon"},
    {"iss": "https://other-ref.supabase.co/auth/v1"},
    {"exp": int(time.time()) - 60},
    {"sub": None},
    {"exp": None},
])
def test_verify_token_rejects_bad_claims(make_token, overrides):
    with pytest.raises(AuthError):
        verify_token(make_token(**overrides))


def test_verify_token_rejects_wrong_signing_key(make_token):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(AuthError):
        verify_token(make_token(key=other_key))


def test_verify_token_rejects_unknown_kid(make_token):
    with pytest.raises(AuthError):
        verify_token(make_token(kid="rotated-away"))


def test_verify_token_rejects_hs256(make_token):
    import jwt
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "exp": int(time.time()) + 60},
        "a-shared-hmac-secret-of-32-bytes!!",
        algorithm="HS256",
        headers={"kid": "test-kid"},
    )

    with pytest.raises(AuthError):
        verify_token(token)


@pytest.mark.parametrize("token", [None, "", "not-a-jwt"])
def test_verify_token_rejects_malformed(make_token, token):
    with pytest.raises(AuthError):
        verify_token(token)


def test_verify_token_requires_supabase_url(make_token, monkeypatch):
    token = make_token()
    monkeypatch.delenv("SUPABASE_URL")

    with pytest.raises(AuthError):
        verify_token(token)
