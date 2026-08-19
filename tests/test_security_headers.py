from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_security_headers_on_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "strict-transport-security" in response.headers
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_security_headers_on_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "strict-transport-security" in response.headers
