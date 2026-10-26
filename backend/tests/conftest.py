import json
import copy
import pytest

class FakeCursor:
    def __init__(self, fetchone_values=None, fetchall_values=None, rowcount=0, raise_on_execute=None):
        self._fetchone_values = list(fetchone_values or [])
        self._fetchall_values = list(fetchall_values or [])
        self.rowcount = rowcount
        self.executed = []
        self.executemany_calls = []
        self.raise_on_execute = raise_on_execute

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self.raise_on_execute:
            raise self.raise_on_execute

    def executemany(self, query, params=None):
        self.executemany_calls.append((query, params))
        if self.raise_on_execute:
            raise self.raise_on_execute

    def fetchone(self):
        return self._fetchone_values.pop(0) if self._fetchone_values else None

    def fetchall(self):
        return self._fetchall_values.pop(0) if self._fetchall_values else []

    def close(self):
        return None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def mock_event():
    return {
        "httpMethod": "GET",
        "resource": "/meals",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "test-auth-user-id",
                    "email": "test@example.com"
                }
            }
        }
    }


@pytest.fixture
def event_copy(mock_event):
    return copy.deepcopy(mock_event)


@pytest.fixture
def fake_cursor():
    return FakeCursor()


@pytest.fixture
def fake_connection(fake_cursor):
    return FakeConnection(fake_cursor)


SUPABASE_TEST_URL = "https://test-ref.supabase.co"


@pytest.fixture(scope="session")
def rsa_private_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def make_token(rsa_private_key, monkeypatch):
    """
    Point auth at a fake Supabase project whose JWKS holds a locally generated
    RSA key, and return a function that mints access tokens signed by it.
    """
    import time
    import jwt
    from backend.shared import auth as auth_module

    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(rsa_private_key.public_key()))
    public_jwk.update({"kid": "test-kid", "alg": "RS256", "use": "sig"})
    jwks_requests = []

    def fake_fetch_data(self):
        jwks_requests.append(self.uri)
        return {"keys": [public_jwk]}

    monkeypatch.setenv("SUPABASE_URL", SUPABASE_TEST_URL)
    monkeypatch.setattr(auth_module, "_jwks_client", None)
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fake_fetch_data)

    def _make_token(key=None, kid="test-kid", **overrides):
        now = int(time.time())
        claims = {
            "sub": "test-auth-user-id",
            "email": "test@example.com",
            "aud": "authenticated",
            "iss": f"{SUPABASE_TEST_URL}/auth/v1",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or rsa_private_key, algorithm="RS256", headers={"kid": kid})

    _make_token.jwks_requests = jwks_requests
    return _make_token
