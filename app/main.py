import json
import logging
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request, status,  Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from fastapi.exceptions import StarletteHTTPException
from app.schemas import CalculationRequest
from app.database import redis_client
from app.scheduler import start_background_tasks, run_bcv_worker, run_binance_worker
from typing import Optional, Literal

# Configuración del Logger
logger = logging.getLogger("uvicorn.error")

APP_ENV = os.getenv("APP_ENV", "development")
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_origins:
    ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]
elif APP_ENV == "production":
    ALLOWED_ORIGINS = []  # en producción sin explícitos → CORS restrictivo
else:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

logger.info(f"Modo: {APP_ENV} | CORS origins: {ALLOWED_ORIGINS}")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- CÓDIGO DE INICIO ---
    logger.info("Iniciando servicios de AhorraVE...")

    # 1. Tareas de carga inicial
    await run_bcv_worker()
    await run_binance_worker()

    # 2. Iniciar el scheduler y guardarlo en el estado de la app
    app.state.scheduler = start_background_tasks()

    logger.info("Scheduler y servicios iniciados correctamente.")
    yield  # Aquí es donde corre tu API

    # --- CÓDIGO DE CIERRE ---
    logger.info("Apagando servicios de AhorraVE...")
    app.state.scheduler.shutdown()
APP_ENV = os.getenv("APP_ENV", "development")
app = FastAPI(
    title="AhorraVE API",
    description="""
    API para la gestión de tasas cambiarias en Venezuela.
    Esta API permite obtener tasas actualizadas del BCV y Binance, 
    consultar el historial de precios y calcular la opción más conveniente 
    entre dos pagos (ej: USD vs VES).
    """,
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
    version="1.0.0",
    lifespan=lifespan
)


# ========== Middleware CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Middleware de Seguridad (OWASP Headers) ==========
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ========== MANEJADORES DE ERRORES ==========
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error inesperado en {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Error interno", "message": "Estamos experimentando problemas técnicos."}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Recurso no encontrado" if exc.status_code == 404 else exc.detail}
    )

# ========== ENDPOINTS ==========

@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica el estado de salud de la API y la conexión a la caché."""
    return {"status": "ok"}

@app.get("/api/v1/rates/bcv", tags=["Tasas"])
async def get_bcv_rates():
    """
    Retorna la **tasa actual del BCV**.
    La información es obtenida desde la caché de Redis, actualizada automáticamente por el worker de fondo.
    """
    data = redis_client.get("rates:bcv")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa BCV no disponible")
    return json.loads(data) if isinstance(data, str) else data

@app.get("/api/v1/rates/binance", tags=["Tasas"])
async def get_binance_rates():
    """
    Retorna la **tasa actual de Binance P2P** (USDT/VES).
    El valor representa el mejor precio de venta actual en la plataforma.
    """
    data = redis_client.get("rates:binance")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa Binance no disponible")
    return json.loads(data) if isinstance(data, str) else data

@app.get("/api/v1/rates/history/{category}", tags=["Historial"])
async def get_rates_history(
    category: Literal["bcv", "binance"],
    limit: int = Query(default=20, gt=0, le=100, description="Número de registros históricos a recuperar")
):
    """
    Obtiene los **últimos registros históricos** de tasas.
    Útil para mostrar gráficas de comportamiento del precio en el tiempo.
    """
    history_key = f"history:rates:{category}"
    raw_history = redis_client.zrevrange(history_key, 0, limit - 1)
    parsed = [json.loads(item) for item in raw_history]
    return {"category": category, "history": parsed}

security = HTTPBasic()

def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("ADMIN_USERNAME", "admin")
    correct_password = os.getenv("ADMIN_PASSWORD", "changeme")
    
    if (credentials.username == correct_username and 
            credentials.password == correct_password):
        return credentials
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Admin Credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
@app.get("/debug/scheduler", tags=["Sistema"])
async def get_scheduler_status(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(verify_admin_credentials)
):
    """Retorna el estado de los trabajos programados."""
    scheduler = request.app.state.scheduler
    jobs = scheduler.get_jobs()
    status = []
    for job in jobs:
        status.append({
            "id": job.id,
            "next_run": str(job.next_run_time),
            "func": job.func_ref
        })
    return {"jobs": status}


@app.post("/api/v1/calcular", tags=["Calculadora"])
async def calculate(request: CalculationRequest):
    """
    **Calcula cuál método de pago es más conveniente.**
    
    Compara dos precios en distintas monedas/fuentes y determina el ahorro real 
    basándose en la tasa de cambio vigente.
    """
    source = request.preferred_source.upper()
    rates_data = redis_client.get(f"rates:{source.lower()}")
    
    if not rates_data:
        raise HTTPException(status_code=503, detail="Tasa no disponible")
    
    rates = json.loads(rates_data) if isinstance(rates_data, str) else rates_data
    rates = rates.get("rates", {})
    usd_rate = float(rates.get("USD") or rates.get("USDT", 0.00))
    
    def to_ves(price, type_):
        types = {"USD": price * usd_rate, "VES": price, "EUR": price * float(rates.get("EUR", usd_rate * 1.08))}
        return types.get(type_, price)
    
    val_a, val_b = to_ves(request.price_a, request.type_a), to_ves(request.price_b, request.type_b)
    best = "OPTION_A" if val_a <= val_b else "OPTION_B"
    savings = abs(val_a - val_b) / (usd_rate if request.target_currency == "USD" else 1)
    
    return {
        "best_option": best,
        "savings": round(savings, 2),
        "details": {"a_ves": round(val_a, 2), "b_ves": round(val_b, 2)}
    }
@app.get("/", tags=["Sistema"])
async def root():
    return {
        "message": "Bienvenido a la API de AhorraVE",
        "docs": "/docs",
        "status": "healthy"
    }
