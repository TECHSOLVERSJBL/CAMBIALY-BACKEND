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
async def test_get_rates_history_pagination(client, db_session_factory, monkeypatch):
    from app.models import RateHistory

    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)
    rows = [
        RateHistory(category="bcv", source="BCV", last_updated=float(1000 + i), rates={"USD": float(i)})
        for i in range(25)
    ]
    async with db_session_factory() as session:
        session.add_all(rows)
        await session.commit()

    response = await client.get("/api/v3/rates/history/bcv?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["total_records"] == 25
    assert len(data["history"]) == 10

    response = await client.get("/api/v3/rates/history/bcv?page=3&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 3
    assert len(data["history"]) == 5

    response = await client.get("/api/v3/rates/history/bcv?page=0&size=10")
    assert response.status_code == 422

    response = await client.get("/api/v3/rates/history/bcv?page=1&size=200")
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
async def test_history_single_date_returns_whole_day(client, db_session_factory, monkeypatch):
    """start_date solo → TODAS las tasas de ese día (00:00:00 a 23:59:59), sin filtrar por hora."""
    from app.models import RateHistory
    from datetime import datetime, timezone

    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)

    def ts(y, m, d, h=0, mi=0):
        return datetime(y, m, d, h, mi, 0, tzinfo=timezone.utc).timestamp()

    rows = [
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 1, 8, 0), rates={"USD": 1.0}),
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 1, 12, 0), rates={"USD": 2.0}),
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 1, 23, 30), rates={"USD": 3.0}),
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 2, 10, 0), rates={"USD": 4.0}),
    ]
    async with db_session_factory() as session:
        session.add_all(rows)
        await session.commit()

    response = await client.get("/api/v3/rates/history/bcv?start_date=2026-06-01&size=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    assert [h["rates"]["USD"] for h in data["history"]] == [3.0, 2.0, 1.0]


@pytest.mark.asyncio
async def test_history_date_range_inclusive(client, db_session_factory, monkeypatch):
    """start_date + end_date → rango inclusivo de días completos."""
    from app.models import RateHistory
    from datetime import datetime, timezone

    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)

    def ts(y, m, d, h=0, mi=0):
        return datetime(y, m, d, h, mi, 0, tzinfo=timezone.utc).timestamp()

    rows = [
        RateHistory(category="ars", source="Frankfurter", last_updated=ts(2026, 6, 1, 10, 0), rates={"USD": 1.0}),
        RateHistory(category="ars", source="Frankfurter", last_updated=ts(2026, 6, 2, 10, 0), rates={"USD": 2.0}),
        RateHistory(category="ars", source="Frankfurter", last_updated=ts(2026, 6, 3, 10, 0), rates={"USD": 3.0}),
        RateHistory(category="ars", source="Frankfurter", last_updated=ts(2026, 6, 5, 10, 0), rates={"USD": 5.0}),
    ]
    async with db_session_factory() as session:
        session.add_all(rows)
        await session.commit()

    response = await client.get("/api/v3/rates/history/ars?start_date=2026-06-01&end_date=2026-06-03&size=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    assert {h["rates"]["USD"] for h in data["history"]} == {1.0, 2.0, 3.0}


@pytest.mark.asyncio
async def test_history_date_range_invalid(client, db_session_factory, monkeypatch):
    """end_date antes que start_date → 400."""
    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)
    response = await client.get("/api/v3/rates/history/bcv?start_date=2026-06-05&end_date=2026-06-01")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_history_invalid_date_format(client, db_session_factory, monkeypatch):
    """Formato de fecha inválido → 422; ISO8601 completo se tolera (pydantic trunca a fecha)."""
    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)
    response = await client.get("/api/v3/rates/history/bcv?start_date=no-es-una-fecha")
    assert response.status_code == 422

    response = await client.get("/api/v3/rates/history/bcv?start_date=2026-06-01T00:00:00Z")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_history_single_date_param(client, db_session_factory, monkeypatch):
    """`date=` → TODAS las tasas de ese día completo, sin filtrar por hora."""
    from app.models import RateHistory
    from datetime import datetime, timezone

    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)

    def ts(y, m, d, h=0, mi=0):
        return datetime(y, m, d, h, mi, 0, tzinfo=timezone.utc).timestamp()

    rows = [
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 1, 8, 0), rates={"USD": 1.0}),
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 1, 23, 30), rates={"USD": 3.0}),
        RateHistory(category="bcv", source="BCV", last_updated=ts(2026, 6, 2, 10, 0), rates={"USD": 4.0}),
    ]
    async with db_session_factory() as session:
        session.add_all(rows)
        await session.commit()

    response = await client.get("/api/v3/rates/history/bcv?date=2026-06-01&size=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2
    assert [h["rates"]["USD"] for h in data["history"]] == [3.0, 1.0]


@pytest.mark.asyncio
async def test_history_date_param_exclusive(client, db_session_factory, monkeypatch):
    """`date=` mezclado con start_date/end_date → 400."""
    monkeypatch.setattr("app.main.AsyncSessionLocal", db_session_factory)
    response = await client.get("/api/v3/rates/history/bcv?date=2026-06-01&start_date=2026-06-01")
    assert response.status_code == 400

    response = await client.get("/api/v3/rates/history/bcv?date=2026-06-01&end_date=2026-06-03")
    assert response.status_code == 400