#!/usr/bin/env python3
"""One-shot: migra history:rates:* de Redis (ZSET) → rate_history (Postgres/Neon).

Uso (contra la instancia real, local o producción):
    uv run python scripts/backfill.py
"""
import asyncio
import json
import sys

from app.database import redis_client, AsyncSessionLocal
from app.models import RateHistory

CATEGORIES = ["bcv", "binance", "cop", "ars"]


async def backfill() -> None:
    if AsyncSessionLocal is None:
        raise SystemExit("DATABASE_URL no configurado — no hay Postgres destino")

    total = 0
    for category in CATEGORIES:
        key = f"history:rates:{category}"
        raw = redis_client.zrange(key, 0, -1, withscores=True)
        rows = [
            RateHistory(
                category=category,
                source=json.loads(payload).get("source", category),
                last_updated=float(score),
                rates=json.loads(payload).get("rates", {}),
            )
            for payload, score in raw
        ]
        async with AsyncSessionLocal() as session:
            session.add_all(rows)
            await session.commit()
        total += len(rows)
        print(f"{key}: {len(rows)} filas")

    print(f"Total migrado: {total}")


if __name__ == "__main__":
    asyncio.run(backfill())