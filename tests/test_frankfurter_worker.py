import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.scrapers import FrankfurterWorker


@pytest.mark.asyncio
async def test_frankfurter_worker_cop():
    """FrankfurterWorker con COP retorna VES por 1 COP."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "COP",
        "quote": "VES",
        "rate": 0.23204
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="COP", redis_key="rates:cop")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.fetch_rate()

    assert "USD" in result
    assert isinstance(result["USD"], float)
    assert result["USD"] > 0
    assert result["USD"] == 0.23204


@pytest.mark.asyncio
async def test_frankfurter_worker_ars():
    """FrankfurterWorker con ARS retorna VES por 1 ARS."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "ARS",
        "quote": "VES",
        "rate": 0.49587
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="ARS", redis_key="rates:ars")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.fetch_rate()

    assert result["USD"] == 0.49587


@pytest.mark.asyncio
async def test_frankfurter_worker_usd():
    """FrankfurterWorker con USD retorna VES por 1 USD."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "USD",
        "quote": "VES",
        "rate": 743.22
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="USD", redis_key="rates:usd")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.fetch_rate()

    assert result["USD"] == 743.22


@pytest.mark.asyncio
async def test_frankfurter_worker_url_correct():
    """Verifica que la URL use /v2/rate/{fiat}/VES."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "COP",
        "quote": "VES",
        "rate": 0.23204
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="COP", redis_key="rates:cop")
    with patch("httpx.AsyncClient", return_value=mock_client) as mock_httpx:
        await worker.fetch_rate()
        called_url = mock_client.__aenter__.return_value.get.call_args[0][0]
        assert called_url == "https://api.frankfurter.dev/v2/rate/COP/VES"


@pytest.mark.asyncio
async def test_frankfurter_worker_http_error():
    """FrankfurterWorker lanza excepción si la API responde error."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 500")

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="COP", redis_key="rates:cop")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.run()

    assert result is None


@pytest.mark.asyncio
async def test_frankfurter_worker_missing_rate():
    """FrankfurterWorker lanza excepción si rate viene null."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "COP",
        "quote": "VES",
        "rate": None
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    worker = FrankfurterWorker(fiat="COP", redis_key="rates:cop")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.run()

    assert result is None


@pytest.mark.asyncio
async def test_frankfurter_worker_full_run(mock_redis):
    """FrankfurterWorker.run() completa el ciclo completo (fetch + redis)."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "date": "2026-07-29",
        "base": "COP",
        "quote": "VES",
        "rate": 0.23204
    })

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    mock_redis.set = MagicMock(return_value=True)
    mock_redis.zadd = MagicMock(return_value=1)

    worker = FrankfurterWorker(fiat="COP", redis_key="rates:cop")
    worker.redis = mock_redis

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await worker.run()

    assert result is not None
    assert result["source"] == "Frankfurter"
    assert result["rates"]["USD"] == 0.23204
    mock_redis.set.assert_called_once()
    mock_redis.zadd.assert_called_once()
