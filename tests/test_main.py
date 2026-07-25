import pytest


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_bcv_rates(client):
    response = await client.get("/api/v1/rates/bcv")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_get_binance_rates(client):
    response = await client.get("/api/v1/rates/binance")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_calcular_missing_fields(client):
    response = await client.post("/api/v1/calcular", json={})
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_get_rates_history_pagination(client):
    from app.database import redis_client
    import json

    history_key = "history:rates:bcv"
    redis_client._history[history_key] = []
    for i in range(25):
        ts = 1000 + i
        payload = json.dumps({"rate": i, "ts": ts})
        redis_client._history[history_key].append((ts, payload))
    redis_client._history[history_key].sort(key=lambda x: x[0])

    response = await client.get("/api/v2/rates/history/bcv?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["total_records"] == 25
    assert len(data["history"]) == 10

    response = await client.get("/api/v2/rates/history/bcv?page=3&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert len(data["history"]) == 5

    response = await client.get("/api/v2/rates/history/bcv?page=0&size=10")
    assert response.status_code == 422

    response = await client.get("/api/v2/rates/history/bcv?page=1&size=200")
    assert response.status_code == 422