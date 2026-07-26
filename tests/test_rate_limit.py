import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import redis_client

client = TestClient(app, raise_server_exceptions=False)

VALID_PAYLOAD = {
    "price_a": 20.00,
    "type_a": "USD",
    "price_b": 920.00,
    "type_b": "VES",
    "target_currency": "USD",
    "preferred_source": "BINANCE"
}

# Seed rate data for calcular endpoint
redis_client.set("rates:binance", json.dumps({"source": "Binance", "last_updated": "2026-07-26T12:00:00Z", "rates": {"USD": 46.50}}))


def test_rate_limit_returns_429_after_10_requests():
    """After 10 requests, the 11th must return 429."""
    responses = []
    for _ in range(11):
        response = client.post("/api/v1/calcular", json=VALID_PAYLOAD)
        responses.append(response.status_code)

    assert responses[-1] == 429, f"Expected 429 on 11th request, got {responses[-1]}"
    for i, code in enumerate(responses[:-1], 1):
        assert code != 429, f"Request #{i} should not be 429, got {code}"


def test_rate_limit_response_body():
    """The 429 response must contain a clean JSON message."""
    for _ in range(11):
        response = client.post("/api/v1/calcular", json=VALID_PAYLOAD)

    assert response.status_code == 429
    body = response.json()
    assert "error" in body
    assert "Demasiadas solicitudes" in body["error"]
