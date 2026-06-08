# app/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scrapers import BCVWorker, BinanceWorker
from app.services import ping_upstash_redis

logger = logging.getLogger("uvicorn.error")


async def run_bcv_worker():
    try:
        worker = BCVWorker()
        await worker.run()
    except Exception as e:
        logger.error(f"Error en BCVWorker: {e}")


async def run_binance_worker():
    try:
        worker = BinanceWorker()
        await worker.run()
    except Exception as e:
        logger.error(f"Error en BinanceWorker: {e}")


def start_background_tasks():
    """Configura, arranca y retorna el scheduler."""
    scheduler = AsyncIOScheduler()

    # 1. Keep-Alive a Upstash-Redis (Cada 5 minutos)
    scheduler.add_job(
        ping_upstash_redis,
        'interval',
        minutes=5,
        id='job_ping_redis',
        replace_existing=True,
        misfire_grace_time = 30
    )

    # 2. Scraper Binance P2P (Cada 15 minutos)
    scheduler.add_job(
        run_binance_worker,
        'interval',
        minutes=15,
        id='job_binance_scraper',
        replace_existing=True,
        misfire_grace_time = 30
    )

    # 3. Scraper BCV (Lunes-Viernes, 11:00-18:00)
    scheduler.add_job(
        run_bcv_worker,
        'cron',
        day_of_week='mon-fri',
        hour='11-18',
        minute='0,30',
        id='job_bcv_scraper',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler iniciado: Tareas automatizadas activas.")

    # IMPORTANTE: Retornar el objeto scheduler para el control del lifespan
    return scheduler