# app/services.py
import logging
from app.database import redis_client

# Usamos el logger de uvicorn para ver los mensajes en la consola de Docker
logger = logging.getLogger("uvicorn.error")

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