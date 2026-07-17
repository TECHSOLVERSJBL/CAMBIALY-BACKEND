import pytest
from app.schemas import CalculationRequest, CalculationResponse


def test_calculation_request_valid():
    data = {
        "amount": 100,
        "rate": 36.5,
        "method": "binance"
    }
    req = CalculationRequest(**data)
    assert req.amount == 100
    assert req.rate == 36.5


def test_calculation_request_invalid():
    with pytest.raises(Exception):
        CalculationRequest(amount=-1, rate=36.5, method="binance")