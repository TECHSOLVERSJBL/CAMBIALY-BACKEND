# app/database.py 
# a 
import os
import json
from dotenv import load_dotenv

load_dotenv()


class MockRedis:
    def __init__(self):
        self._data = {}
        print("Usando MockRedis (sin conexión a Upstash)")
    
    def get(self, key):
        return self._data.get(key)
    
    def set(self, key, value):
        if isinstance(value, dict):
            self._data[key] = value
        else:
            self._data[key] = value
        return True


# Ver si debemos usar Upstash
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
APP_ENV = os.getenv("APP_ENV", "development")

# === DIAGNÓSTICO ===
print(f"DEBUG: APP_ENV = '{APP_ENV}'")
print(f"DEBUG: UPSTASH_URL = '{UPSTASH_URL[:30] if UPSTASH_URL else 'NO SET'}'...")
print(f"DEBUG: UPSTASH_TOKEN = {'SET' if UPSTASH_TOKEN else 'NO SET'}")
print(f"DEBUG: production check = {APP_ENV == 'production'}")
print(f"DEBUG: URL check = {bool(UPSTASH_URL)}")
print(f"DEBUG: TOKEN check = {bool(UPSTASH_TOKEN)}")
# === FIN DIAGNÓSTICO ===

if APP_ENV == "production" and UPSTASH_URL and UPSTASH_TOKEN:
    try:
        from upstash_redis import Redis
        redis_client = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)
        # Probar conexión
        redis_client.ping()
        print(" Conectado a Upstash Redis (producción)")
    except Exception as e:
        print(f" Error Upstash: {e}, usando MockRedis")
        redis_client = MockRedis()
else:
    print(" Usando MockRedis (APP_ENV no es production o faltan credenciales)")
    redis_client = MockRedis()

redis_db = redis_client