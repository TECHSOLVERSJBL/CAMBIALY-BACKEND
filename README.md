## **API** Calculadora de Conveniencia Cambiaria (**VES**/**USD**/**EUR**)

Este proyecto consiste en una **API** **REST** automatizada y de alta velocidad diseñada para calcular en tiempo real qué método de pago (divisas en efectivo o bolívares a tasa oficial/paralela) resulta más conveniente al realizar una compra en Venezuela.

El objetivo es resolver un problema cotidiano: la pérdida de dinero por redondeos mal calculados o brechas cambiarias entre comercios y tasas oficiales.

## 🏗️ Arquitectura del Sistema (Explicación Sencilla)

Para soportar un alto tráfico de usuarios sin saturar los servidores ni ser bloqueados por las páginas de origen, el backend no consulta el BCV ni Binance en cada cálculo. En su lugar, utiliza un patrón de **Caché**:

1. **El Recolector (Scraper/API Worker):** Un script asíncrono se ejecuta en segundo plano cada ciertas horas. Visita la página del BCV, extrae las tasas del Dólar y Euro, y consulta la API de Binance.
2. **La Memoria Rápida (Redis Caché):** El recolector guarda las tasas del día en una base de datos en memoria (Redis). Leer de aquí toma menos de 2 milisegundos.
3. **El Motor (FastAPI):** Cuando un usuario ingresa montos a la calculadora, FastAPI toma las tasas guardadas en Redis, realiza la matemática al instante y devuelve la recomendación de compra.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.10+
* **Framework Web:** `FastAPI` (Asíncrono, ultrarápido y genera documentación automática).
* **Extracción de Datos:** `HTTPX` (Peticiones HTTP asíncronas) y `BeautifulSoup4` (Web Scraping para el BCV).
* **Caché y Base de Datos:** `Redis` (Almacenamiento temporal ultraveloz en la nube vía Upstash).
* **Servidor de Producción:** `Uvicorn`.
* **Contenedores**: `Docker` y `Docker Compose` (Para empaquetar y ejecutar la aplicación en cualquier entorno de forma estandarizada).


## 🔌 Endpoints de la API (Rutas)
La API expondrá principalmente dos rutas que el Frontend o la App móvil consumirán:

### **1. Obtener Tasas del Día**

Ruta: `GET /api/v1/tasas`

**Descripción**: Devuelve los valores actuales del Dólar BCV, Euro BCV, y Binance P2P en Bolívares guardados en caché.

Resultado de la petición (**JSON**): 

```JSON
{
  "fecha_actualizacion": "2026-05-28T12:00:00Z",
  "bcv": {
    "usd": 41.50,
    "eur": 44.82
  },
  "binance_p2p": {
    "usd": 45.20,
    "eur": 48.90
  }
}
```

### 2. Calcular Conveniencia

Ruta: `POST /api/v1/calcular`

**Descripción**: Recibe los precios del producto en la tienda y calcula cuál opción es mejor.

Cuerpo de la Petición (**JSON**):

```JSON
{
  "monto_divisa": 50.00,
  "monto_bolivares": 2000.00,
  "moneda": "USD" 
}
```

Respuesta (**JSON**):

```JSON
{
  "conviene_pagar_en": "BOLIVARES",
  "ahorro_estimado_usd": 1.81,
  "tasa_tienda_aplicada": 40.00,
  "tasa_oficial_bcv": 41.50,
  "detalle": "Si pagas en bolívares estás aprovechando una tasa menor a la oficial. Al pagar en divisas estarías perdiendo el equivalente a 1.81 USD."
}
```

Plan de Desarrollo (Cronograma de 2 Semanas)

#### Semana 1: Extracción y Lógica Central (Backend Puro) 

* Día 1-2: Configuración del entorno de Python, instalación de dependencias, repositorios Git y archivos de Docker. 
 * Día 3-4: Desarrollo de app/scrapers.py. Crear funciones asíncronas para extraer tasas de **BCV** y Binance. 
 * Día 5-7: Conexión con Upstash Redis. Guardar los datos y estructurar la lógica en services.py.

####  Semana 2: **API**, Despliegue y Pruebas 

* Día 8-10: Creación de los endpoints en app/main.py. Probar los requests desde Swagger (/docs). 
* Día 11-12: Configuración de tareas en segundo plano para mantener Redis actualizado automáticamente. 
* Día 13-14: Construcción de la imagen Docker final y despliegue en producción (Render, Koyeb o **VPS**). Pruebas de carga.

Configuración Local (Método Tradicional)

### Clonar el repositorio:

git clone https://github.com/watchtheblind/ahorrave-backend.git cd ahorrave-backend
### Crear e inicializar el Entorno Virtual: 
```shell 
python -m venv venv 
```

En Windows: ```.\venv\Scripts\activate ```

En Linux/Mac: ```source venv/bin/activate ```

### Instalar dependencias: 
```shell 
pip install -r requirements.txt 
```

### Correr la API en modo desarrollo: 
```shell 
uvicorn app.main:app --reload
```

Configuración Local (Usando Docker)

Usar Docker facilita ejecutar el proyecto de forma idéntica en cualquier computadora, sin necesidad de configurar Python ni entornos virtuales manualmente.

Requisitos: Tener Docker y Docker Desktop (o Docker Compose) instalado.

### Construir y ejecutar el contenedor: 

En la misma carpeta donde se encuentra el archivo docker-compose.yml, ejecuta: 

```shell 
docker-compose up --build
```

Este comando descargará el entorno de Python, instalará las dependencias y ejecutará la **API**. Si deseas que corra en segundo plano (liberando tu terminal), añade la bandera -d al final: docker-compose up --build -d

### Detener los contenedores:

Si ejecutaste el comando normal, presiona Ctrl + C en tu terminal. Si lo corriste en segundo plano, ejecuta: docker-compose down

### Probar la **API**

Sin importar si usaste el método tradicional o Docker, una vez que el servidor esté corriendo, abre tu navegador web y visita: [http://**127**.0.0.1:**8000**/docs](https://[www.google.com/search?q=http://**127**.0.0.1:**8000**/docs](https://www.google.com/search?q=http://**127**.0.0.1:**8000**/docs))

Allí encontrarás la interfaz gráfica de Swagger, donde podrás probar todas las rutas y enviar datos de prueba a la calculadora fácilmente.
