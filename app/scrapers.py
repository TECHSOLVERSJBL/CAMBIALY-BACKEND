import httpx
import re
import json
import logging
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime
from app.database import redis_db

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
                payload = {
                    "source": self.__class__.__name__.replace("Worker", ""),
                    "last_updated": datetime.now().isoformat() + "Z",
                    "rates": rates
                }
                # Save to Redis
                self.redis.set(self.redis_key, json.dumps(payload))
                logger.info(f"Successfully updated {self.redis_key}")
                return payload
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}: {str(e)}")
            return None


class BCVWorker(BaseRateWorker):
    def __init__(self):
        super().__init__(redis_key="rates:bcv")
        self.url = "https://www.bcv.org.ve/"

    def _extract_number(self, element) -> float:
        """Helper to clean and extract numbers from HTML elements."""
        if not element:
            return None

        # Priority containers based on BCV structure
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
        async with httpx.AsyncClient(verify=False) as client:  # BCV often has SSL issues
            response = await client.get(self.url, timeout=30.0)
            if response.status_code != 200:
                raise Exception(f"BCV returned status {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Logic for USD and EUR using IDs
            usd_element = soup.find(id="dolar")
            eur_element = soup.find(id="euro")

            rates = {
                "USD": self._extract_number(usd_element),
                "EUR": self._extract_number(eur_element)
            }

            # Basic validation
            if not rates["USD"]:
                logger.warning("Could not find USD rate, check BCV HTML structure.")

            return {k: round(v, 2) for k, v in rates.items() if v is not None}


class BinanceWorker(BaseRateWorker):
    def __init__(self):
        super().__init__(redis_key="rates:binance")
        # Placeholder for Binance P2P API or similar
        self.api_url = "https://p2p.binance.com/bapi/c2c/v2/public/c2c/adv/quoted"

    async def fetch_rate(self) -> dict:
        """Logic for Binance P2P (Placeholder for now)."""
        # Aquí implementaremos luego la lógica de Binance
        return {"USDT": 0.00}  # Mock data