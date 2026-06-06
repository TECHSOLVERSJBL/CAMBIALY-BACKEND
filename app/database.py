# app/database.py 
import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

class MockRedis:
    def __init__(self):
        self._data = {}
        self._history = {}  # <-- Almacenará las listas para el simulador de historial
        print("Usando MockRedis (sin conexión a Upstash)")
    
    def get(self, key):
        return self._data.get(key)
    
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

# Ver si debemos usar Upstash
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
APP_ENV = os.getenv("APP_ENV", "development")

print(f"DEBUG: APP_ENV = '{APP_ENV}'")
print(f"DEBUG: UPSTASH_URL = '{UPSTASH_URL[:40] if UPSTASH_URL else 'NO SET'}'...")
print(f"DEBUG: UPSTASH_TOKEN = {'SET' if UPSTASH_TOKEN else 'NO SET'}")

if APP_ENV == "production" and UPSTASH_URL and UPSTASH_TOKEN:
    try:
        # Usar redis-py en lugar de upstash_redis (más estable)
        import redis
        
        # Parsear la URL de Upstash (formato: https://xxxx.upstash.io)
        # Extraer el host (quitar https:// y .upstash.io)
        host = UPSTASH_URL.replace("https://", "").replace("http://", "")
        
        redis_client = redis.Redis(
            host=host,
            port=6379,
            password=UPSTASH_TOKEN,
            ssl=True,
            decode_responses=True
        )
        # Probar conexión
        redis_client.ping()
        print("Conectado a Upstash Redis (vía redis-py)")
    except Exception as e:
        print(f"Error Upstash: {e}, usando MockRedis")
        redis_client = MockRedis()
else:
    print("Usando MockRedis (condición no cumplida)")
    redis_client = MockRedis()

redis_db = redis_client