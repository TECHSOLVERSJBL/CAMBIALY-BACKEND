from pydantic import BaseModel, Field,field_validator 
from typing import Literal, Optional, Union
from datetime import datetime

currencies = Literal["USD", "VES", "EUR", "COP", "ARS"]
class CalculationRequest(BaseModel):
    price_a: float = Field(gt=0)
    price_b: float = Field(gt=0)
    type_a: currencies
    type_b: currencies
    preferred_source: Literal["BCV", "BINANCE"]
    target_currency: currencies
    
class CalculationResponse(BaseModel):
    request_summary: dict
    calculation_details: dict
    recommendation: dict


class RateResponseDTO(BaseModel):
    source: str
    target_currency: str
    rate_value: float
    last_updated: str


class RateHistoricalDTO(BaseModel):
    currency: str
    rate: float
    timestamp: str
    rate_value: Optional[float] = None
    last_updated: Optional[str] = None
    target_currency: Optional[str] = None
    source: Optional[str] = None