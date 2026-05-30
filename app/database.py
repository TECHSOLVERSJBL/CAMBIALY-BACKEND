import os
import redis
from dotenv import load_dotenv

load_dotenv()
def get_redis_client():
    return redis.from_url(
        os.getenv("REDIS_URL"), 
        decode_responses=True
    )

# global instance so you can import it
redis_client = get_redis_client()
