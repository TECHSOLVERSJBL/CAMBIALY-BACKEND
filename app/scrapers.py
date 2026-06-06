import httpx
import re
import json
import logging
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime
from app.database import redis_client as redis_db

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
                
                # 1. Guardar el estado actual en Redis (como ya lo hacías)
                self.redis.set(self.redis_key, payload_json)
                
                # 2. Guardar en el Historial Ordenado (NUEVO)
                # Usamos el timestamp actual como score para mantener el orden cronológico
                timestamp = int(current_time.timestamp())
                history_key = f"history:{self.redis_key}"
                
                # redis-py espera un diccionario con la estructura {valor: score}
                self.redis.zadd(history_key, {payload_json: timestamp})
                
                logger.info(f"Successfully updated current rate and history for {self.redis_key}")
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
        # Endpoint correcto para Binance P2P
        self.api_url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

    async def fetch_rate(self) -> dict:
        """
        Obtiene la tasa de cambio USDT/VES desde Binance P2P.
        Busca el mejor precio de VENTA (SELL) de USDT para recibir bolívares.
        """
        try:
            # Parámetros para buscar ofertas de venta de USDT en bolívares
            payload = {
                "asset": "USDT",           # Criptomoneda a vender
                "fiat": "VES",             # Moneda local (Bolívares Venezolanos)
                "tradeType": "SELL",       # SELL = vendes USDT, recibes VES
                "page": 1,
                "rows": 5,                 # Traemos las 5 mejores ofertas
                "payTypes": [],            # Sin filtrar por método de pago
                "publisherType": None,     # Sin filtrar por tipo de publicador
                "merchantCheck": True      # Verificar merchant
            }
            
            # Headers para evitar bloqueos
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
                    logger.error(f"Binance P2P returned status {response.status_code}")
                    raise Exception(f"Binance P2P returned status {response.status_code}")
                
                data = response.json()
                
                # Verificar código de respuesta
                if data.get("code") != "000000":
                    logger.error(f"Binance P2P API error code: {data.get('code')}")
                    raise Exception(f"Binance P2P API error: {data.get('message', 'Unknown error')}")
                
                # Verificar que hay datos
                if not data.get("data") or len(data["data"]) == 0:
                    logger.warning("No se encontraron ofertas en Binance P2P para VES")
                    # Devolver último valor conocido? Por ahora lanzamos excepción
                    raise Exception("No se encontraron ofertas en Binance P2P para VES")
                
                # Tomamos el mejor precio (primera oferta ordenada por mejor precio)
                # Las ofertas vienen ordenadas por mejor precio automáticamente
                first_offer = data["data"][0]
                price = float(first_offer["adv"]["price"])
                
        
                
                
                logger.info(f"Binance P2P USDT/VES rate: {price} Bs/USDT")
                
                # Devolvemos como USD para mantener consistencia con el resto de la API
                return {"USD": round(price, 2)}
                
        except httpx.TimeoutException:
            logger.error("Timeout al conectar con Binance P2P")
            raise Exception("Timeout connecting to Binance P2P")
        except httpx.RequestError as e:
            logger.error(f"Error de red al conectar con Binance P2P: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en BinanceWorker: {str(e)}")
            raise