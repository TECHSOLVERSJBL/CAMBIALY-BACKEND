import pytest
from app.schemas import CalculationRequest, CalculationResponse


def test_calculation_request_valid():
    data = {
        "price_a": 20.00,
        "type_a": "USD",
        "price_b": 920.00,
        "type_b": "VES",
        "target_currency": "USD",
        "preferred_source": "BINANCE"
    }
    req = CalculationRequest(**data)
    assert req.price_a == 20.00
    assert req.type_a == "USD"


def test_calculation_request_invalid():
    with pytest.raises(Exception):
        CalculationRequest(
            price_a=-1,
            type_a="USD",
            price_b=920.00,
            type_b="VES",
            target_currency="USD",
            preferred_source="BINANCE"
        )