import json
import logging
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request, status, Depends, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from fastapi.exceptions import StarletteHTTPException
from app.schemas import CalculationRequest, RateResponseDTO, RateHistoricalDTO
from app.database import redis_client, AsyncSessionLocal
from app.models import RateHistory
from app.scheduler import start_background_tasks, run_bcv_worker, run_binance_worker, run_cop_worker, run_ars_worker
from typing import Optional, Literal, Union
from datetime import date, datetime, timezone
from sqlalchemy import func, select
from app.utils import datetime_to_unix
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

limiter = Limiter(key_func=get_remote_address)

logger.info(f"Modo: {APP_ENV} | CORS origins: {ALLOWED_ORIGINS}")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- CÓDIGO DE INICIO ---
    logger.info("Iniciando servicios de AhorraVE...")

    # WILL REFACTOR
    await run_bcv_worker()
    await run_binance_worker()
    await run_cop_worker()
    await run_ars_worker()

    # 2. Iniciar el scheduler y guardarlo en el estado de la app
    app.state.scheduler = start_background_tasks()

    logger.info("Scheduler y servicios iniciados correctamente.")
    yield  # Aquí es donde corre tu API

    # --- CÓDIGO DE CIERRE ---
    logger.info("Apagando servicios de AhorraVE...")
    app.state.scheduler.shutdown()
APP_ENV = os.getenv("APP_ENV", "development")
app = FastAPI(
    title="Cambialy API",
    description="""
    API para la gestión de tasas cambiarias en Venezuela.
    Esta API permite obtener tasas actualizadas del BCV, Binance y Yadio, 
    consultar el historial de precios y calcular la opción más conveniente 
    entre dos pagos (ej: USD vs VES).

    ⚖️ **Descargo de Responsabilidad / Disclaimer**
    Los datos proporcionados por esta API son de carácter **meramente informativo**
    y se obtienen de fuentes públicas de terceros (BCV, Binance, Yadio.io).
    No constituyen asesoramiento financiero, recomendación de inversión ni
    garantía de exactitud en tiempo real. El uso de la información es bajo
    la exclusiva responsabilidad del usuario.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Demasiadas solicitudes. Intenta de nuevo en un minuto."}
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
    safe_messages = {
        400: "Solicitud inválida",
        401: "No autorizado",
        403: "Acceso prohibido",
        404: "Recurso no encontrado",
        405: "Método no permitido",
        422: "Error de validación",
        500: "Error interno del servidor",
        503: "Servicio no disponible",
    }
    detail = safe_messages.get(exc.status_code, "Error del servidor")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail}
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


def _rate_history_to_payload(row: RateHistory) -> dict:
    """Convierte una fila de Postgres al payload JSON que devolvía el ZSET de Redis."""
    return {
        "source": row.source,
        "last_updated": datetime.fromtimestamp(row.last_updated, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "rates": row.rates,
    }


@app.get("/api/v2/rates/history/{category}", tags=["Historial"])
async def get_rates_history_v2(
    category: Literal["bcv", "binance", "cop", "ars"],
    page: int = Query(default=1, ge=1, description="Número de página"),
    size: int = Query(default=50, ge=1, le=100, description="Registros por página (máx 100)"),
    cursor: Optional[str] = Query(None, description="Cursor de paginación (ISO8601 o timestamp Unix)"),
    start_date: Optional[date] = Query(None, description="Filtro inicio (YYYY-MM-DD). Solo esta fecha → TODAS las tasas de ese día"),
    end_date: Optional[date] = Query(None, description="Filtro fin (YYYY-MM-DD). Con start_date forma rango inclusivo de días completos")
):
    """
    Obtiene los **últimos registros históricos** de tasas con paginación por cursor o por páginas.
    Versión 2 — incluye metadatos de paginación y cursor para scrolling infinito.
    El historial se lee de Postgres (durable); Redis solo sirve la tasa actual.

    Filtro por fecha (YYYY-MM-DD):
    - `start_date` solo → TODAS las tasas de ese día completo (00:00:00 a 23:59:59).
    - `start_date` + `end_date` → rango inclusivo de días completos.
    """
    if AsyncSessionLocal is None:
        raise HTTPException(status_code=503, detail="Historial no disponible: DATABASE_URL no configurado")
    logger.info(f"[API V2 History] Req category={category}, page={page}, size={size}, cursor={cursor}")

    async with AsyncSessionLocal() as session:
        if cursor:
            try:
                if cursor.endswith("Z") or "T" in cursor:
                    max_ts = datetime_to_unix(datetime.fromisoformat(cursor.replace("Z", "+00:00")))
                else:
                    max_ts = float(cursor)
            except Exception as err:
                logger.error(f"[API V2 History] Error parsing cursor '{cursor}': {err}")
                raise HTTPException(status_code=400, detail="Formato de cursor inválido")

            total_records = (
                await session.execute(
                    select(func.count()).select_from(RateHistory).where(RateHistory.category == category)
                )
            ).scalar_one()
            stmt = (
                select(RateHistory)
                .where(RateHistory.category == category, RateHistory.last_updated < max_ts)
                .order_by(RateHistory.last_updated.desc())
                .limit(size + 1)
            )
        else:
            offset = (page - 1) * size
            stmt = select(RateHistory).where(RateHistory.category == category)
            if start_date or end_date:
                if start_date and end_date and end_date < start_date:
                    raise HTTPException(status_code=400, detail="end_date debe ser mayor o igual que start_date")
                min_ts = datetime_to_unix(datetime.combine(start_date, datetime.min.time())) if start_date else 0
                max_ts = datetime_to_unix(datetime.combine(end_date, datetime.max.time())) if end_date else datetime_to_unix(datetime.combine(start_date, datetime.max.time()))
                stmt = stmt.where(RateHistory.last_updated >= min_ts, RateHistory.last_updated <= max_ts)
            total_records = (
                await session.execute(select(func.count()).select_from(stmt.subquery()))
            ).scalar_one()
            stmt = stmt.order_by(RateHistory.last_updated.desc()).offset(offset).limit(size + 1)

        rows = (await session.execute(stmt)).scalars().all()

    has_more = len(rows) > size
    if has_more:
        rows = rows[:size]

    parsed = [_rate_history_to_payload(row) for row in rows]
    next_cursor = parsed[-1].get("last_updated") if (has_more and parsed) else None
    logger.info(f"[API V2 History] Page query returned {len(parsed)} items. total_records={total_records}, next_cursor={next_cursor}, has_more={has_more}")

    return {
        "category": category,
        "page": page,
        "size": size,
        "total_records": total_records,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "history": parsed
    }


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
@limiter.limit("10/minute")
async def calculate(request: Request, calculation: CalculationRequest):
    """
    **Calcula cuál método de pago es más conveniente.**
    
    Compara dos precios en distintas monedas/fuentes y determina el ahorro real 
    basándose en la tasa de cambio vigente.
    """
    source = calculation.preferred_source.upper()
    rates_data = redis_client.get(f"rates:{source.lower()}")
    
    if not rates_data:
        raise HTTPException(status_code=503, detail="Tasa no disponible")
    
    rates = json.loads(rates_data) if isinstance(rates_data, str) else rates_data
    rates = rates.get("rates", {})
    usd_rate = float(rates.get("USD") or rates.get("USDT", 0.00))
    
    def to_ves(price, type_):
        types = {"USD": price * usd_rate, "VES": price, "EUR": price * float(rates.get("EUR", usd_rate * 1.08))}
        return types.get(type_, price)
    
    val_a, val_b = to_ves(calculation.price_a, calculation.type_a), to_ves(calculation.price_b, calculation.type_b)
    best = "OPTION_A" if val_a <= val_b else "OPTION_B"
    savings = abs(val_a - val_b) / (usd_rate if calculation.target_currency == "USD" else 1)
    
    return {
        "best_option": best,
        "savings": round(savings, 2),
        "details": {"a_ves": round(val_a, 2), "b_ves": round(val_b, 2)}
    }
# ========== V2 — Rutas explícitas por tipo de activo ==========

rates_router_v2 = APIRouter(prefix="/api/v2/rates", tags=["Tasas V2"])


def _historical_rate(history_key: str, rate_field: str, date: datetime, currency: str) -> RateHistoricalDTO:
    """Busca la tasa más cercana en el historial de Redis para la fecha indicada."""
    ts = datetime_to_unix(date)
    raw = redis_client.zrevrangebyscore(history_key, ts, 0, start=0, num=1)
    if not raw:
        raw = redis_client.zrangebyscore(history_key, ts, "+inf", start=0, num=1)
    if not raw:
        raw = redis_client.zrevrange(history_key, 0, 0)
    if not raw:
        raise HTTPException(status_code=404, detail=f"No hay datos para {currency} en la fecha indicada")

    payload = json.loads(raw[0])
    rates = payload.get("rates", {})
    rate = rates.get(rate_field)
    if rate is None:
        rate = rates.get("USDT") or rates.get("USD") or (list(rates.values())[0] if rates else None)
    if rate is None:
        raise HTTPException(status_code=404, detail=f"No hay datos para {currency} en la fecha indicada")

    ts_str = payload.get("last_updated") or date.strftime("%Y-%m-%dT%H:%M:%SZ")
    return RateHistoricalDTO(
        currency=currency,
        rate=float(rate),
        timestamp=ts_str,
        rate_value=float(rate),
        last_updated=ts_str,
        target_currency=currency,
        source=payload.get("source", "Historical")
    )


@rates_router_v2.get("/usd", response_model=Union[RateResponseDTO, RateHistoricalDTO])
async def get_usd_rate(
    date: Optional[datetime] = Query(None, description="Fecha/hora ISO8601 para consulta histórica. Ej: 2026-06-15T14:30:00Z. Cuando se provee, retorna {currency, rate, timestamp} en lugar de RateResponseDTO.")
):
    """
    Retorna la **tasa oficial del Dólar (USD)** según el BCV.
    - Sin `?date=`: devuelve `RateResponseDTO` con la tasa más reciente.
    - Con `?date=`: busca en el historial la tasa más cercana a la fecha indicada y retorna `{currency, rate, timestamp}`.
    """
    if date:
        return _historical_rate("history:rates:bcv", "USD", date, "USD")
    data = redis_client.get("rates:bcv")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa USD no disponible")
    payload = json.loads(data) if isinstance(data, str) else data
    usd_rate = payload.get("rates", {}).get("USD")
    if usd_rate is None:
        raise HTTPException(status_code=404, detail="Tasa USD no disponible")
    return RateResponseDTO(
        source=payload.get("source"),
        target_currency="USD",
        rate_value=usd_rate,
        last_updated=payload.get("last_updated")
    )


@rates_router_v2.get("/eur", response_model=Union[RateResponseDTO, RateHistoricalDTO])
async def get_eur_rate(
    date: Optional[datetime] = Query(None, description="Fecha/hora ISO8601 para consulta histórica. Ej: 2026-06-15T14:30:00Z. Cuando se provee, retorna {currency, rate, timestamp} en lugar de RateResponseDTO.")
):
    """
    Retorna la **tasa oficial del Euro (EUR)** según el BCV.
    - Sin `?date=`: devuelve `RateResponseDTO` con la tasa más reciente.
    - Con `?date=`: busca en el historial la tasa más cercana a la fecha indicada y retorna `{currency, rate, timestamp}`.
    """
    if date:
        return _historical_rate("history:rates:bcv", "EUR", date, "EUR")
    data = redis_client.get("rates:bcv")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa EUR no disponible")
    payload = json.loads(data) if isinstance(data, str) else data
    eur_rate = payload.get("rates", {}).get("EUR")
    if eur_rate is None:
        raise HTTPException(status_code=404, detail="Tasa EUR no disponible")
    return RateResponseDTO(
        source=payload.get("source"),
        target_currency="EUR",
        rate_value=eur_rate,
        last_updated=payload.get("last_updated")
    )


@rates_router_v2.get("/usdt", response_model=Union[RateResponseDTO, RateHistoricalDTO])
async def get_usdt_rate(
    date: Optional[datetime] = Query(None, description="Fecha/hora ISO8601 para consulta histórica. Ej: 2026-06-15T14:30:00Z. Cuando se provee, retorna {currency, rate, timestamp} en lugar de RateResponseDTO.")
):
    """
    Retorna el **precio promedio USDT/VES** desde Binance P2P.
    - Sin `?date=`: devuelve `RateResponseDTO` con la tasa más reciente.
    - Con `?date=`: busca en el historial la tasa más cercana a la fecha indicada y retorna `{currency, rate, timestamp}`.
    """
    if date:
        return _historical_rate("history:rates:binance", "USD", date, "USDT")
    data = redis_client.get("rates:binance")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa USDT no disponible")
    payload = json.loads(data) if isinstance(data, str) else data
    usdt_rate = payload.get("rates", {}).get("USD")
    if usdt_rate is None:
        raise HTTPException(status_code=404, detail="Tasa USDT no disponible")
    return RateResponseDTO(
        source=payload.get("source"),
        target_currency="USDT",
        rate_value=usdt_rate,
        last_updated=payload.get("last_updated")
    )


@rates_router_v2.get("/cop", response_model=Union[RateResponseDTO, RateHistoricalDTO])
async def get_cop_rate(
    date: Optional[datetime] = Query(None, description="Fecha/hora ISO8601 para consulta histórica. Ej: 2026-06-15T14:30:00Z. Cuando se provee, retorna {currency, rate, timestamp} en lugar de RateResponseDTO.")
):
    """
    Retorna la **tasa del Peso Colombiano (COP)** vía Yadio.io.
    - Sin `?date=`: devuelve `RateResponseDTO` con la tasa más reciente.
    - Con `?date=`: busca en el historial la tasa más cercana a la fecha indicada y retorna `{currency, rate, timestamp}`.
    """
    if date:
        return _historical_rate("history:rates:cop", "USD", date, "COP")
    data = redis_client.get("rates:cop")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa COP no disponible")
    payload = json.loads(data) if isinstance(data, str) else data
    cop_rate = payload.get("rates", {}).get("USD")
    if cop_rate is None:
        raise HTTPException(status_code=404, detail="Tasa COP no disponible")
    return RateResponseDTO(
        source=payload.get("source"),
        target_currency="COP",
        rate_value=cop_rate,
        last_updated=payload.get("last_updated")
    )


@rates_router_v2.get("/ars", response_model=Union[RateResponseDTO, RateHistoricalDTO])
async def get_ars_rate(
    date: Optional[datetime] = Query(None, description="Fecha/hora ISO8601 para consulta histórica. Ej: 2026-06-15T14:30:00Z. Cuando se provee, retorna {currency, rate, timestamp} en lugar de RateResponseDTO.")
):
    """
    Retorna la **tasa del Peso Argentino (ARS)** vía Yadio.io.
    - Sin `?date=`: devuelve `RateResponseDTO` con la tasa más reciente.
    - Con `?date=`: busca en el historial la tasa más cercana a la fecha indicada y retorna `{currency, rate, timestamp}`.
    """
    if date:
        return _historical_rate("history:rates:ars", "USD", date, "ARS")
    data = redis_client.get("rates:ars")
    if not data:
        raise HTTPException(status_code=404, detail="Tasa ARS no disponible")
    payload = json.loads(data) if isinstance(data, str) else data
    ars_rate = payload.get("rates", {}).get("USD")
    if ars_rate is None:
        raise HTTPException(status_code=404, detail="Tasa ARS no disponible")
    return RateResponseDTO(
        source=payload.get("source"),
        target_currency="ARS",
        rate_value=ars_rate,
        last_updated=payload.get("last_updated")
    )


app.include_router(rates_router_v2)


@app.get("/", tags=["Sistema"])
async def root():
    return {
        "message": "Bienvenido a la API de Cambialy. Consulta /docs para ver la documentación completa.",
        "docs": "/docs",
        "status": "healthy",
        "disclaimer": ("""
               ⚖️ **Descargo de Responsabilidad / Disclaimer**
               Los datos proporcionados por esta API son de carácter **meramente informativo**
               y se obtienen de fuentes públicas de terceros (BCV, Binance, Yadio.io).
               No constituyen asesoramiento financiero, recomendación de inversión ni
               garantía de exactitud en tiempo real. El uso de la información es bajo
               la exclusiva responsabilidad del usuario.
               """,
        )
    }
