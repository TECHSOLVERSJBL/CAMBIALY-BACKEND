from pydantic import BaseModel, field_validator 
from typing import Literal, Optional
from datetime import datetime

class CalculationRequest(BaseModel):
    price_a: float
    type_a: str
    price_b: float
    type_b: str
    preferred_source: str
    target_currency: str

    @field_validator('preferred_source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v.upper() not in ['BCV', 'BINANCE']:
            raise ValueError('La fuente debe ser BCV o BINANCE')
        return v.upper()

class CalculationResponse(BaseModel):
    request_summary: dict
    calculation_details: dict
    recommendation: dict