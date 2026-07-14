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