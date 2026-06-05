from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class CalculationRequest(BaseModel):
    price_a: float
    type_a: str  # "USD", "VES", "BCV_RATE", "EUR"
    price_b: float
    type_b: str
    target_currency: str = "USD"
    preferred_source: Literal["BCV", "BINANCE"] = "BCV"

class CalculationResponse(BaseModel):
    request_summary: dict
    calculation_details: dict
    recommendation: dict