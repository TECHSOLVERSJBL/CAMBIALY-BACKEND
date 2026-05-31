import redis
import os
from dotenv import load_dotenv

load_dotenv()


class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # Obtenemos las variables del .env
            host = os.getenv("UPSTASH_REDIS_REST_URL")
            port = int(os.getenv("UPSTASH_REDIS_PORT", 6379))
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

            # Creamos la instancia (Singleton)
            cls._instance = redis.Redis(
                host=host,
                port=port,
                password=token,
                decode_responses=True,
                ssl=True  # Needed for upstash
            )
        return cls._instance


# Exporting a single instance for the whole Project
redis_db = RedisClient()