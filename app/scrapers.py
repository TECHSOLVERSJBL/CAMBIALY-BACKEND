import httpx
import re
import json
import logging
import asyncio
import random
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime
from app.database import redis_client as redis_db
from app.services import fetch_yadio_rate

# Configuración de logs para monitorear los workers
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseRateWorker(ABC):
    """
    Abstract base class for all currency scrapers.
    Follows the Template Method Pattern.
    """

    def __init__(self, redis_key: str):
        self.redis = redis_db
        self.redis_key = redis_key

    @abstractmethod
    async def fetch_rate(self) -> dict:
        """Specific implementation for each data source."""
        pass

    async def run(self):
        """Execution flow shared by all workers."""
        try:
            logger.info(f"Starting worker: {self.__class__.__name__}")
            rates = await self.fetch_rate()

            if rates:
                current_time = datetime.now()
                payload = {
                    "source": self.__class__.__name__.replace("Worker", ""),
                    "last_updated": current_time.isoformat() + "Z",
                    "rates": rates
                }

                payload_json = json.dumps(payload)

                # 1. Guardar el estado actual en Redis
                self.redis.set(self.redis_key, payload_json)

                # 2. Guardar en el Historial Ordenado
                timestamp = int(current_time.timestamp())
                history_key = f"history:{self.redis_key}"

                self.redis.zadd(history_key, {payload_json: timestamp})

                logger.info(f"Successfully updated current rate and history for {self.redis_key}")
                return payload

        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}: {str(e)}")
            return None

#WILL REFACTOR...MAYBE MAKE WORKERS EASIER TO READ AND SEPARATE SOME THINGS?
class BCVWorker(BaseRateWorker):
    def __init__(self):
        super().__init__(redis_key="rates:bcv")
        self.url = "https://www.bcv.org.ve/"

    def _extract_number(self, element) -> float:
        """Helper to clean and extract numbers from HTML elements."""
        if not element:
            return None

        targets = [
            element.find('div', class_='centrado'),
            element.find('strong'),
            element.find('span'),
            element
        ]

        for target in targets:
            if target and target.text:
                text = target.text.strip().replace(',', '.').replace(' ', '')
                matches = re.findall(r'(\d+(?:\.\d+)?)', text)
                if matches:
                    try:
                        return float(matches[0])
                    except ValueError:
                        continue
        return None

    async def fetch_rate(self) -> dict:
        """Asynchronous scraping of the BCV website."""
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(self.url, timeout=30.0)
            if response.status_code != 200:
                raise Exception(f"BCV returned status {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')

            usd_element = soup.find(id="dolar")
            eur_element = soup.find(id="euro")

            rates = {
                "USD": self._extract_number(usd_element),
                "EUR": self._extract_number(eur_element)
            }

            if not rates["USD"]:
                logger.warning("Could not find USD rate, check BCV HTML structure.")

            return {k: round(v, 2) for k, v in rates.items() if v is not None}

#WILL REFACTOR
class BinanceWorker(BaseRateWorker):
    def __init__(self):
        super().__init__(redis_key="rates:binance")
        self.api_url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        # User-agents rotativos para disminuir huella de bot
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    async def fetch_rate(self) -> dict:
        """
        Obtiene la tasa de cambio USDT/VES desde Binance P2P.
        Usa la TERCERA oferta (índice 2) para evitar precios anómalos.
        Si ocurre cualquier error o bloqueo, ejecuta el fallback seguro de Yadio.
        """
        try:
            # Jitter dinámico para no realizar peticiones en intervalos robóticos idénticos
            await asyncio.sleep(random.uniform(1, 8))

            payload = {
                "asset": "USDT",
                "fiat": "VES",
                "tradeType": "SELL",
                "page": 1,
                "rows": 10,  # Aumentado para tener suficientes ofertas
                "payTypes": [],
                "publisherType": None,
                "merchantCheck": True
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": random.choice(self.user_agents),
                "Accept": "application/json",
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": "https://p2p.binance.com/"
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"Fetching Binance P2P rates from {self.api_url}")
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=15.0
                )

                if response.status_code != 200:
                    raise Exception(f"Binance P2P returned status {response.status_code}")

                data = response.json()

                if data.get("code") != "000000":
                    raise Exception(f"Binance P2P API error: {data.get('message', 'Unknown error')}")

                ofertas_count = len(data.get("data", []))
                if ofertas_count < 3:
                    logger.warning(f"Solo se encontraron {ofertas_count} ofertas. Usando la última disponible.")
                    oferta_idx = ofertas_count - 1
                else:
                    oferta_idx = 2  # TERCERA oferta (índice 2)
                    logger.info(f"Usando la TERCERA oferta (índice {oferta_idx}) para evitar precios anómalos")

                oferta = data["data"][oferta_idx]
                price = float(oferta["adv"]["price"])

                logger.info(f"Binance P2P USDT/VES rate obtenido exitosamente (oferta #{oferta_idx + 1}): {price} Bs/USDT")
                return {"USD": round(price, 2)}

        except Exception as err:
            # MANEJO INTELIGENTE: Captura cualquier excepción (Network, Timeout, HTTP Error, JSON vacío)
            # e invoca el fallback de servicios de manera transparente.
            logger.warning(f"Error detectado en BinanceWorker ({str(err)}). Activando contingencia con Yadio.io...")
            try:
                backup_price = await fetch_yadio_rate()

                # Si por alguna razón Yadio devuelve el valor de emergencia 0.0, lanzamos error
                if backup_price <= 0.0:
                    raise Exception("El servicio de fallback de Yadio retornó una tasa inválida o nula.")

                logger.info(f"Tasa de reemplazo obtenida desde Yadio con éxito: {backup_price} Bs/USDT")
                return {"USD": round(backup_price, 2)}

            except Exception as fallback_err:
                logger.error(f"Error crítico: El plan B (Yadio) también ha fallado: {str(fallback_err)}")
                # Re-lanzamos la excepción para que el BaseRateWorker la registre y no guarde datos corruptos en Redis
                raise Exception(
                    f"Ambos servicios de tasas (Binance y Yadio) fallaron de forma consecutiva. Deteniendo flujo.")


class YadioRateWorker(BaseRateWorker):
    """Worker genérico para tasas vía Yadio.io, parametrizable por moneda fiat."""

    def __init__(self, fiat: str, redis_key: str):
        super().__init__(redis_key=redis_key)
        self.fiat = fiat.upper()

    async def fetch_rate(self) -> dict:
        url = f"https://api.yadio.io/rate/USDT/{self.fiat}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            rate = data.get("rate")
            if rate is None:
                raise Exception(f"Yadio no devolvió rate para {self.fiat}")
            return {"USD": round(float(rate), 2)}