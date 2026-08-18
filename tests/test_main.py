import pytest
import json


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
    from app.database import redis_client
    redis_client.set("rates:bcv", json.dumps({"source": "BCV", "last_updated": "2026-07-26T12:00:00Z", "rates": {"USD": 45.20, "EUR": 50.10}}))
    response = await client.get("/api/v1/rates/bcv")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_get_binance_rates(client):
    from app.database import redis_client
    redis_client.set("rates:binance", json.dumps({"source": "Binance", "last_updated": "2026-07-26T12:00:00Z", "rates": {"USD": 46.50}}))
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
    for i in range(25):
        ts = 1000 + i
        payload = json.dumps({"rate": i, "ts": ts})
        redis_client.zadd(history_key, {payload: ts})

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


@pytest.mark.asyncio
async def test_get_cop_rate(client):
    from app.database import redis_client
    redis_client.set("rates:cop", json.dumps({"source": "YadioRate", "last_updated": "2026-07-26T12:00:00Z", "rates": {"USD": 4500.50}}))
    response = await client.get("/api/v2/rates/cop")
    assert response.status_code == 200
    data = response.json()
    assert data["target_currency"] == "COP"
    assert data["rate_value"] == 4500.50
    assert data["source"] == "YadioRate"


@pytest.mark.asyncio
async def test_get_ars_rate(client):
    from app.database import redis_client
    redis_client.set("rates:ars", json.dumps({"source": "YadioRate", "last_updated": "2026-07-26T12:00:00Z", "rates": {"USD": 1200.75}}))
    response = await client.get("/api/v2/rates/ars")
    assert response.status_code == 200
    data = response.json()
    assert data["target_currency"] == "ARS"
    assert data["rate_value"] == 1200.75
    assert data["source"] == "YadioRate"


@pytest.mark.asyncio
async def test_history_single_date_returns_whole_day(client):
    """start_date solo → TODAS las tasas de ese día (00:00:00 a 23:59:59), sin filtrar por hora."""
    from app.database import redis_client
    from datetime import datetime, timezone

    history_key = "history:rates:bcv"
    day1 = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    day1_noon = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    day1_night = datetime(2026, 6, 1, 23, 30, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 6, 2, 10, 0, 0, tzinfo=timezone.utc)

    for label, dt in [("a", day1), ("b", day1_noon), ("c", day1_night), ("d", day2)]:
        ts = dt.timestamp()
        redis_client.zadd(history_key, {json.dumps({"rate": label, "ts": ts}): ts})

    response = await client.get("/api/v2/rates/history/bcv?start_date=2026-06-01&size=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    labels = {h["rate"] for h in data["history"]}
    assert labels == {"a", "b", "c"}


@pytest.mark.asyncio
async def test_history_date_range_inclusive(client):
    """start_date + end_date → rango inclusivo de días completos."""
    from app.database import redis_client
    from datetime import datetime, timezone

    history_key = "history:rates:ars"  # categoría propia para aislar del estado compartido
    days = [
        datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 2, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 3, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 5, 10, 0, 0, tzinfo=timezone.utc),
    ]
    for i, dt in enumerate(days):
        ts = dt.timestamp()
        redis_client.zadd(history_key, {json.dumps({"rate": i, "ts": ts}): ts})

    response = await client.get("/api/v2/rates/history/ars?start_date=2026-06-01&end_date=2026-06-03&size=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    labels = {h["rate"] for h in data["history"]}
    assert labels == {0, 1, 2}


@pytest.mark.asyncio
async def test_history_date_range_invalid(client):
    """end_date antes que start_date → 400."""
    response = await client.get("/api/v2/rates/history/bcv?start_date=2026-06-05&end_date=2026-06-01")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_history_invalid_date_format(client):
    """Formato de fecha inválido → 422; ISO8601 completo se tolera (pydantic trunca a fecha)."""
    response = await client.get("/api/v2/rates/history/bcv?start_date=no-es-una-fecha")
    assert response.status_code == 422

    response = await client.get("/api/v2/rates/history/bcv?start_date=2026-06-01T00:00:00Z")
    assert response.status_code == 200