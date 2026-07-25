# app/services.py
import logging
import httpx
from app.database import redis_client
# Usamos el logger de uvicorn para ver los mensajes en la consola de Docker
logger = logging.getLogger("uvicorn.error")


async def fetch_yadio_rate(fiat: str = "VES"):
    """uses USDT/{fiat} rate from Yadio.io as backup."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://api.yadio.io/exchanges/{fiat}")
            response.raise_for_status()
            data = response.json()
            rate = data.get("USDT", {}).get("price")
            return float(rate)

    except Exception as e:
        logger.error(f"Error fatal obteniendo tasa de Yadio ({fiat}): {e}")
        return 0.00

def ping_upstash_redis():
    """
    Realiza un ping síncrono a Redis (Upstash o MockRedis)
    para mantener la conexión activa y evitar que se ponga en modo de suspensión.
    """
    try:
        redis_client.ping()
        logger.info("Keep-alive: Ping exitoso a Redis/Upstash.")
    except Exception as e:
        logger.error(f"Keep-alive: El ping automático falló: {e}")