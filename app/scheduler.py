# app/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scrapers import BCVWorker, BinanceWorker, YadioRateWorker
from app.services import ping_upstash_redis

logger = logging.getLogger("uvicorn.error")

#WILL REFACTOR INTO A GENERIC FUNCTION LATER, FOR NOW IT'S OK TO HAVE IT LIKE THIS. THIS A DRY MESS
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


async def run_cop_worker():
    try:
        worker = YadioRateWorker(fiat="COP", redis_key="rates:cop")
        await worker.run()
    except Exception as e:
        logger.error(f"Error en CopWorker: {e}")


async def run_ars_worker():
    try:
        worker = YadioRateWorker(fiat="ARS", redis_key="rates:ars")
        await worker.run()
    except Exception as e:
        logger.error(f"Error en ArsWorker: {e}")


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

    # 4. Scraper COP (Cada 15 minutos)
    scheduler.add_job(
        run_cop_worker,
        'interval',
        minutes=15,
        id='job_cop_scraper',
        replace_existing=True,
        misfire_grace_time=30
    )

    # 5. Scraper ARS (Cada 15 minutos)
    scheduler.add_job(
        run_ars_worker,
        'interval',
        minutes=15,
        id='job_ars_scraper',
        replace_existing=True,
        misfire_grace_time=30
    )

    scheduler.start()
    logger.info("Scheduler iniciado: Tareas automatizadas activas.")

    # IMPORTANTE: Retornar el objeto scheduler para el control del lifespan
    return scheduler