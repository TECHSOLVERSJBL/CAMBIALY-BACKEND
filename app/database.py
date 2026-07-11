# app/database.py 
import os
import redis
from dotenv import load_dotenv
import logging
load_dotenv()

logger = logging.getLogger(__name__)
class MockRedis:
    def __init__(self):
        self._data = {}
        self._history = {}  # <-- Almacenará las listas para el simulador de historial
        logger.info("Usando Redis Local (sin conexión a Upstash)")
    
    def get(self, key):
        return self._data.get(key)
    
    def ping(self):
        return True
    
    def set(self, key, value):
        self._data[key] = value
        return True

    # === NUEVOS MÉTODOS PARA EL HISTORIAL ===
    def zadd(self, key, mapping):
        """Simula guardar datos en un Sorted Set de Redis"""
        if key not in self._history:
            self._history[key] = []
        
        # mapping es un diccionario dict {json_str: timestamp}
        for value, score in mapping.items():
            # Evitamos duplicados idénticos en la simulación
            self._history[key] = [item for item in self._history[key] if item[1] != value]
            self._history[key].append((score, value))
        
        # Ordenamos por el score (timestamp) de menor a mayor
        self._history[key].sort(key=lambda x: x[0])
        return len(mapping)
        
    def zrevrange(self, key, start, end):
        """Simula obtener elementos en orden descendente (más recientes primero)"""
        if key not in self._history:
            return []
        
        # Invertimos para que los scores más altos (más recientes) estén al principio
        reversed_history = sorted(self._history[key], key=lambda x: x[0], reverse=True)
        
        # Extraemos solo el contenido (el string JSON) omitiendo el score
        just_values = [item[1] for item in reversed_history]
        
        # Aplicamos el rebanado (slicing) posicional de Redis
        return just_values[start:end+1]

# ── Decidir qué Redis usar ──
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")

logger.debug(f"APP_ENV = '{APP_ENV}'")
logger.debug(f"REDIS_URL = {'SET' if REDIS_URL else 'NO SET'}")
logger.debug(f"UPSTASH_URL = '{UPSTASH_URL[:40] if UPSTASH_URL else 'NO SET'}'...")
logger.debug(f"UPSTASH_TOKEN = {'SET' if UPSTASH_TOKEN else 'NO SET'}")
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("Conectado a Redis local")
    except Exception as e:
        logger.error(f"Error REDIS_URL: {e}, usando MockRedis")
        redis_client = MockRedis()
elif APP_ENV == "production" and UPSTASH_URL and UPSTASH_TOKEN:
    try:
        host = UPSTASH_URL.replace("https://", "").replace("http://", "")
        redis_client = redis.Redis(
            host=host, port=6379, password=UPSTASH_TOKEN,
            ssl=True, decode_responses=True
        )
        redis_client.ping()
        logger.info("Conectado a Upstash Redis (vía redis-py)")
    except Exception as e:
        logger.error(f"ERROR - Error Upstash: {e}, usando MockRedis")
        redis_client = MockRedis()
else:
    logger.warning("Usando MockRedis (sin conexión externa)")
    redis_client = MockRedis()

redis_db = redis_client