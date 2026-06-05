from fastapi import FastAPI, HTTPException
from app.schemas import CalculationRequest
from app.database import redis_client
from app.scrapers import BCVWorker, BinanceWorker
import json

app = FastAPI(title="AhorraVE API - Calculadora Cambiaria")

async def run_bcv_worker():
    """Ejecuta el worker del BCV"""
    worker = BCVWorker()
    result = await worker.run()
    return result

async def run_binance_worker():
    """Ejecuta el worker de Binance"""
    worker = BinanceWorker()
    result = await worker.run()
    return result

@app.on_event("startup")
async def startup_event():
    """Ejecuta los workers al iniciar la API"""
    print("Actualizando tasas iniciales...")
    await run_bcv_worker()
    await run_binance_worker()
    print("API lista para usar")

@app.get("/")
async def root():
    return {"message": "AhorraVE API - Calculadora de Conveniencia Cambiaria"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ========== ENDPOINTS ==========

@app.get("/api/v1/rates/bcv")
async def get_bcv_rates():
    """Obtiene tasas del BCV desde Redis"""
    data = redis_client.get("rates:bcv")
    if not data:
        raise HTTPException(status_code=404, detail="Tasas BCV no disponibles")
    
    # Si está guardado como string JSON, parsearlo
    if isinstance(data, str):
        return json.loads(data)
    return data

@app.get("/api/v1/rates/binance")
async def get_binance_rates():
    """Obtiene tasas de Binance desde Redis"""
    data = redis_client.get("rates:binance")
    if not data:
        raise HTTPException(status_code=404, detail="Tasas Binance no disponibles")
    
    if isinstance(data, str):
        return json.loads(data)
    return data

@app.post("/api/v1/calcular")
async def calculate(request: CalculationRequest):
    """Calcula qué opción de pago es más conveniente"""
    # Obtener tasas según preferencia
    if request.preferred_source == "BCV":
        rates_data_raw = redis_client.get("rates:bcv")
    else:
        rates_data_raw = redis_client.get("rates:binance")
    
    if not rates_data_raw:
        raise HTTPException(status_code=503, detail="Tasas no disponibles temporalmente")
    
    # Parsear si es string JSON
    if isinstance(rates_data_raw, str):
        rates_data = json.loads(rates_data_raw)
    else:
        rates_data = rates_data_raw
    
    # Extraer tasa USD
    rates = rates_data.get("rates", {})
    usd_rate = rates.get("USD") or rates.get("USDT", 41.50)
    
    # Normalizar ambas opciones a VES
    def to_ves(price, type_):
        if type_ == "USD":
            return price * usd_rate
        elif type_ == "VES":
            return price
        elif type_ == "BCV_RATE":
            return price * usd_rate
        elif type_ == "EUR":
            eur_rate = rates.get("EUR", usd_rate * 1.08)
            return price * eur_rate
        return price
    
    option_a_ves = to_ves(request.price_a, request.type_a)
    option_b_ves = to_ves(request.price_b, request.type_b)
    
    # Determinar mejor opción
    best = "OPTION_A" if option_a_ves <= option_b_ves else "OPTION_B"
    savings_ves = abs(option_a_ves - option_b_ves)
    
    # Convertir ahorro a moneda objetivo
    if request.target_currency == "USD":
        savings = savings_ves / usd_rate if usd_rate > 0 else 0
    else:
        savings = savings_ves
    
    return {
        "request_summary": {
            "option_a": {"price": request.price_a, "type": request.type_a},
            "option_b": {"price": request.price_b, "type": request.type_b},
            "source_used": request.preferred_source,
            "target_currency": request.target_currency
        },
        "calculation_details": {
            "option_a_in_ves": round(option_a_ves, 2),
            "option_b_in_ves": round(option_b_ves, 2),
            "exchange_rate_applied": usd_rate
        },
        "recommendation": {
            "best_option": best,
            "savings_amount": round(savings, 2),
            "savings_currency": request.target_currency,
            "message": f"La opción {best} es más conveniente. Ahorras {round(savings, 2)} {request.target_currency}"
        }
    }