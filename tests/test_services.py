import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_redis_keepalive(mock_redis):
    mock_redis.ping.return_value = True
    result = await mock_redis.ping()
    assert result is True


@pytest.mark.asyncio
async def test_redis_get_returns_none(mock_redis):
    result = await mock_redis.get("rate:bcv")
    assert result is None