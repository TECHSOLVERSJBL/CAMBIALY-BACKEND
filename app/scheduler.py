# app/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scrapers import BCVWorker, BinanceWorker
from app.services import ping_upstash_redis

logger = logging.getLogger("uvicorn.error")

# Mudamos los ejecutores aquí para no ensuciar el main
async def run_bcv_worker():
    """Ejecuta el worker del BCV"""
    worker = BCVWorker()
    return await worker.run()

async def run_binance_worker():
    """Ejecuta el worker de Binance"""
    worker = BinanceWorker()
    return await worker.run()

def start_background_tasks():
    """Configura y arranca todas las tareas automatizadas en segundo plano"""
    scheduler = AsyncIOScheduler()
    
    # 1. Keep-Alive a Upstash-Redis (Cada 5 minutos)
    scheduler.add_job(
        ping_upstash_redis, 
        'interval', 
        minutes=5, 
        id='job_ping_redis'
    )
    
    # 2. Scraper Binance P2P (Cada 15 minutos)
    scheduler.add_job(
        run_binance_worker, 
        'interval', 
        minutes=15, 
        id='job_binance_scraper'
    )
    
    # 3. Scraper BCV (Lunes a Viernes, 11:00 AM - 6:00 PM, en los minutos 0 y 30)
    scheduler.add_job(
        run_bcv_worker, 
        'cron', 
        day_of_week='mon-fri', 
        hour='11-18', 
        minute='0,30', 
        id='job_bcv_scraper'
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado: Tareas automatizadas activas.")
    return scheduler