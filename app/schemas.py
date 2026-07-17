from pydantic import BaseModel, Field,field_validator 
from typing import Literal, Optional
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