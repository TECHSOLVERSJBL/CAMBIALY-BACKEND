import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

SENSITIVE_PATTERNS = [
    r"File \"",
    r"line \d+",
    r"Traceback",
    r"app[/\\]",
    r"venv[/\\]",
    r"__pycache__",
    r"import ",
    r"def ",
    r"class ",
]


def _contains_sensitive_info(text: str) -> bool:
    return any(re.search(p, text) for p in SENSITIVE_PATTERNS)


def test_unhandled_exception_returns_clean_500():
    @app.get("/test-crash")
    async def crash():
        raise RuntimeError("DB connection lost at line 42 in database.py")

    response = client.get("/test-crash")
    assert response.status_code == 500

    body = response.json()
    assert "error" in body
    assert "RuntimeError" not in str(body)
    assert "database.py" not in str(body)
    assert "line 42" not in str(body)
    assert not _contains_sensitive_info(str(body))

    del app.router.routes[-1]


def test_http_404_does_not_leak_detail():
    response = client.get("/nonexistent-route-xyz")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert not _contains_sensitive_info(str(body))


def test_http_405_returns_generic_message():
    response = client.post("/health")
    assert response.status_code == 405
    body = response.json()
    assert "error" in body
    assert not _contains_sensitive_info(str(body))


def test_unhandled_exception_logs_error(capsys):
    @app.get("/test-crash-logged")
    async def crash_logged():
        raise ValueError("Secret internal value: abc123")

    response = client.get("/test-crash-logged")
    assert response.status_code == 500
    body = response.json()
    assert "Secret internal value" not in str(body)
    assert "abc123" not in str(body)

    del app.router.routes[-1]
