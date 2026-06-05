# app/database.py 
import os
import json
from dotenv import load_dotenv

load_dotenv()


class MockRedis:
    def __init__(self):
        self._data = {}
        print("Usando MockRedis")
    
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

if APP_ENV == "production" and UPSTASH_URL and UPSTASH_TOKEN:
    try:
        from upstash_redis import Redis
        redis_client = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)
        print(" Conectado a Upstash Redis")
    except Exception as e:
        print( "Error Upstash:, usando MockRedis")
        redis_client = MockRedis()
else:
    redis_client = MockRedis()

redis_db = redis_client