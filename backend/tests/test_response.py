import importlib


def test_response_uses_allowed_origin(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://example.com")

    from backend.shared import response as response_module
    importlib.reload(response_module)

    try:
        resp = response_module.response(200, {"ok": True})
        assert resp["headers"]["Access-Control-Allow-Origin"] == "http://example.com"
    finally:
        monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)
        importlib.reload(response_module)


def test_response_default_origin(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)

    from backend.shared import response as response_module
    importlib.reload(response_module)

    resp = response_module.response(200, {"ok": True})
    assert resp["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
