
- [AHORRAVE](#ahorrave)
   * [**API** Exchange Convenience Calculator (**VES**/**USD**/**EUR**)](#api-exchange-convenience-calculator-vesusdeur)
   * [🏗️ System Architecture](#-system-architecture)
   * [📁 Folder structure ](#-folder-structure)
      + [Quick Overview:](#quick-overview)
      + [Structure considerations](#structure-considerations)
   * [🛠️ Technologies Used](#-technologies-used)
   * [🔌 API Endpoints (Routes)](#-api-endpoints-routes)
      + [**1. Get BCV Day Rates**](#1-get-bcv-day-rates)
      + [**2. Get Binance Daily Rates**](#2-get-binance-daily-rates)
      + [2. Calculate Convenience](#2-calculate-convenience)
      + [What would this look like in practice?](#what-would-this-look-like-in-practice)
         - [Case 1: Compare cash vs. transfer (Rate of the day)](#case-1-compare-cash-vs-transfer-rate-of-the-day)
         - [Case 2: The trade has "phantom" prices at the BCV rate](#case-2-the-trade-has-phantom-prices-at-the-bcv-rate)
         - [Case 3: You want to see if the store rate beats the black market (Binance)](#case-3-you-want-to-see-if-the-store-rate-beats-the-black-market-binance)
   * [Development Plan (2 Week Schedule)](#development-plan-2-week-schedule)
         - [Week 1: Extraction and Core Logic (Pure Backend) ](#week-1-extraction-and-core-logic-pure-backend)
         - [Week 2: **API**, Deployment and Testing ](#week-2-api-deployment-and-testing)
      + [Clone the repository:](#clone-the-repository)
      + [Create and initialize the Virtual Environment: ](#create-and-initialize-the-virtual-environment)
      + [Install dependencies: ](#install-dependencies)
      + [Run the API in development mode: ](#run-the-api-in-development-mode)
      + [Build and run the container: ](#build-and-run-the-container)
      + [Stop containers:](#stop-containers)
      + [Test the **API** AND DIAGRAMS](#test-the-api-and-diagrams)
      + [Data State Diagram](#data-state-diagram)
      + [Data flow diagram](#data-flow-diagram)
      + [Data Model Diagram (Redis)](#data-model-diagram-redis)
      + [Normalization Decision Diagram](#normalization-decision-diagram)
   * [Production Deployment Guide (Render + Upstash)](#production-deployment-guide-render-upstash)
      + [1. Database: Upstash Redis](#1-database-upstash-redis)
      + [2. API deployment: Render](#2-api-deployment-render)
      + [3. Solving common problems in production](#3-solving-common-problems-in-production)
         - [Mistake: `cannot import name 'Redis' from 'upstash_redis'`](#mistake-cannot-import-name-redis-from-upstash_redis)
         - [Mistake: `Error Upstash: usando MockRedis`](#mistake-error-upstash-usando-mockredis)
      + [4. Local Development (without Upstash)](#4-local-development-without-upstash)
      + [5. Future updates](#5-future-updates)
   * [❓ FAQ: Technical Project Decisions](#-faq-technical-project-decisions)
      + [1. Why FastAPI and not another framework like Flask or Django?](#1-why-fastapi-and-not-another-framework-like-flask-or-django)
      + [2. Why do we need Redis? Isn't a normal database enough?](#2-why-do-we-need-redis-isnt-a-normal-database-enough)
      + [3. Why do we include "Background Tasks"?](#3-why-do-we-include-background-tasks)
      + [4. Is this level of complexity really necessary for something so "small"?](#4-is-this-level-of-complexity-really-necessary-for-something-so-small)
      + [5. How do scrapers work?](#5-how-do-scrapers-work)

<!-- TOC end -->

<!-- TOC --><a name="and-a-table-of-contents"></a>
## And a table of contents

will be generated

<!-- TOC --><a name="on-the-right"></a>
## On   the right
<!-- TOC --><a name="ahorrave"></a>
# AHORRAVE
<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [**API** Exchange Convenience Calculator (**VES**/**USD**/**EUR**)](#api-calculadora-de-conveniencia-cambiaria-vesusdeur)
- [🏗️ System Architecture](#-arquitectura-del-sistema)
- [📁 Folder structure ](#-estructura-de-carpetas)
   * [Quick Overview:](#descripción-rápida)
   * [Structure considerations](#consideraciones-acerca-de-la-estructura)
- [🛠️ Technologies Used](#-tecnologías-utilizadas)
- [🔌 API Endpoints (Routes)](#-endpoints-de-la-api-rutas)
   * [**1. Get BCV Day Rates**](#1-obtener-tasas-del-día-bcv)
   * [**2. Get Binance Daily Rates**](#2-obtener-tasas-del-día-binance)
   * [2. Calculate Convenience](#2-calcular-conveniencia)
   * [What would this look like in practice?](#cómo-se-vería-esto-en-la-práctica)
      + [Case 1: Compare cash vs. transfer (Rate of the day)](#caso-1-comparar-efectivo-vs-transferencia-tasa-del-día)
      + [Case 2: The trade has "phantom" prices at the BCV rate](#caso-2-el-comercio-tiene-precios-fantasma-a-tasa-bcv)
      + [Case 3: You want to see if the store rate beats the black market (Binance)](#caso-3-quieres-ver-si-la-tasa-de-la-tienda-le-gana-al-mercado-negro-binance)
- [Development Plan (2 Week Schedule)](#plan-de-desarrollo-cronograma-de-2-semanas)
      + [Week 1: Extraction and Core Logic (Pure Backend) ](#semana-1-extracción-y-lógica-central-backend-puro)
      + [Week 2: **API**, Deployment and Testing ](#semana-2-api-despliegue-y-pruebas)
   * [Clone the repository:](#clonar-el-repositorio)
   * [Create and initialize the Virtual Environment: ](#crear-e-inicializar-el-entorno-virtual)
   * [Install dependencies: ](#instalar-dependencias)
   * [Run the API in development mode: ](#correr-la-api-en-modo-desarrollo)
   * [Build and run the container: ](#construir-y-ejecutar-el-contenedor)
   * [Stop containers:](#detener-los-contenedores)
   * [Test the **API** AND DIAGRAMS](#probar-la-api-y-diagramas)
   * [Data State Diagram](#diagrama-de-estado-de-datos)
   * [Data flow diagram](#diagrama-de-flujo-de-datos)
   * [Data Model Diagram (Redis)](#diagrama-de-modelo-de-datos-redis)
   * [Normalization Decision Diagram](#diagrama-de-decisión-de-normalización)
- [❓ FAQ: Technical Project Decisions](#-faq-decisiones-técnicas-del-proyecto)
   * [1. Why FastAPI and not another framework like Flask or Django?](#1-por-qué-fastapi-y-no-otro-framework-como-flask-o-django)
   * [2. Why do we need Redis? Isn't a normal database enough?](#2-por-qué-necesitamos-redis-no-basta-con-una-base-de-datos-normal)
   * [3. Why do we include "Background Tasks"?](#3-por-qué-incluimos-tareas-en-segundo-plano-background-tasks)
   * [4. Is this level of complexity really necessary for something so "small"?](#4-es-realmente-necesario-este-nivel-de-complejidad-para-algo-tan-pequeño)
   * [5. How do scrapers work?](#5-cómo-funcionan-los-scrapers)


<!-- TOC end -->
<!-- TOC --><a name="api-exchange-convenience-calculator-vesusdeur"></a>
## **API** Exchange Convenience Calculator (**VES**/**USD**/**EUR**)

This project consists of an automated, high-speed **API** **REST** designed to calculate in real time which payment method (cash foreign exchange or bolivars at the official/parallel rate) is most convenient when making a purchase in Venezuela.

The objective is to solve an everyday problem: the loss of money due to poorly calculated rounding or exchange gaps between businesses and official rates.

<!-- TOC --><a name="-system-architecture"></a>
## 🏗️ System Architecture

To support high user traffic without overwhelming the servers or being blocked by the originating pages, the backend does not consult the BCV or Binance in each calculation. Instead, use a **Cache** pattern:

1. **The Scraper (Scraper/API Worker):** An asynchronous script runs in the background every few hours. Visit the BCV page, extract the Dollar and Euro rates, and consult the Binance API.
2. **Fast Memory (Redis Cache):** The collector saves the day's rates in an in-memory database (Redis). Reading from here takes less than 2 milliseconds.
3. **The Engine (FastAPI):** When a user enters amounts into the calculator, FastAPI takes the rates saved in Redis, performs the math instantly and returns the purchase recommendation.

<!-- TOC --><a name="-folder-structure"></a>
## 📁 Folder structure 

To maintain order, scalability and clarity, the files are structured as follows:

```text
ahorrave-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada de la API
│   ├── schemas.py           # Modelos de Pydantic (validación de JSON)
│   ├── services.py          # Lógica de negocio (normalización y cálculos)
│   ├── database.py          # Conexión con Upstash Redis
│   ├── scrapers.py          # Workers (lógica de BCV y Binance)
│   └── utils.py             # Funciones auxiliares (fechas, helpers)
├── tests/                   # Pruebas unitarias para la lógica de cálculo
├── .env                     # Variables de entorno (Redis URL, Tokens)
├── docker-compose.yml       # Orquestación de contenedores
├── Dockerfile               # Configuración del entorno Python
├── requirements.txt         # Dependencias
└── README.md                # Documentación del proyecto

```

---

<!-- TOC --><a name="quick-overview"></a>
### Quick Overview:

* **`app/main.py`**: This is where we define the routes (`/api/v1/rates/bcv`, `/api/v1/rates/binance` and `/api/v1/calcular`). It just delegates the work to the other files.
* **`app/schemas.py`**: It is the "contract" of the API. Here we define the JSONs that we saw before (`CalculationRequest`, `CalculationResponse`). If the data does not come as we expect, FastAPI will fail here before reaching the logic.
* **`app/services.py`**: Here resides the **normalization decision diagram**. It's where the magic happens: you receive the data from the schema, query Redis, normalize to `VES` and you compare.
* **`app/scrapers.py`**: It will have two main functions (e.g.: `update_bcv_rates` and `update_binance_rates`). Each one will be an asynchronous task that the system will call according to its own frequency.
* **`app/database.py`**: Connection management with `redis-py`. Keeps connection code clean and reusable.

<!-- TOC --><a name="structure-considerations"></a>
### Structure considerations

1. **Scalability:** If tomorrow you want to add a third scraper (for example, for the Euro or rates from another website), you just create the function in `scrapers.py` and add a route in `main.py`.
2. **Maintainability:** If there is a mathematical error in the calculation, you know it is in `services.py`. If the data is getting bad, you know it's in `scrapers.py`.
3. **Testing:** By separating the logic (`services.py`) from the web (`main.py`), you can do unit testing without having to build a web server.


---

<!-- TOC --><a name="-technologies-used"></a>
## 🛠️ Technologies Used

* **Language:** Python 3.10+
* **Web Framework:** `FastAPI` (Asynchronous, ultra-fast and generates automatic documentation).
* **Data Extraction:** `HTTPX` (asynchronous HTTP requests) and `BeautifulSoup4` (Web Scraping for the BCV).
* **Cache and Database:** `Redis` (Ultra-fast temporary cloud storage via Upstash).
* **Production Server:** `Uvicorn`.
* **Containers**: `Docker` and `Docker Compose` (To package and run the application in any environment in a standardized way).


<!-- TOC --><a name="-api-endpoints-routes"></a>
## 🔌 API Endpoints (Routes)
The API will mainly expose two routes that the Frontend or Mobile App will consume:

<!-- TOC --><a name="1-get-bcv-day-rates"></a>
### **1. Get BCV Day Rates**

Route: `GET /api/v1/rates/bcv`

**Description**: Returns the official rates (USD/EUR) of the Central Bank of Venezuela.

**Purpose**: Returns the official rates (USD/EUR) of the Central Bank of Venezuela.

**Frequency**: Update via scheduled task (cron) from 11:00 AM to 6:00 PM.

**Storage**: key `rates: bcv` in Redis.

Request result (**JSON**): 

```JSON
{
  "source": "BCV",
  "last_updated": "2026-05-29T15:30:00Z",
  "rates": {
    "USD": 41.50,
    "EUR": 44.82
  }
}
```
<!-- TOC --><a name="2-get-binance-daily-rates"></a>
### **2. Get Binance Daily Rates**

Route: `GET /api/v1/rates/bcv`

**Description**: Returns Binance P2P rate

**Purpose**: Constant update every 10-15 minutes due to high volatility.

**Frequency**: Update via scheduled task (cron) from 11:00 AM to 6:00 PM.

**Storage**: key `rates: binance` in Redis.

Request result (**JSON**): 

```JSON
{
  "source": "Binance P2P",
  "last_updated": "2026-05-29T15:35:00Z",
  "rates": {
    "USD": 45.20
  }
}
```

<!-- TOC --><a name="2-calculate-convenience"></a>
### 2. Calculate Convenience

Route: `POST /api/v1/calcular`

**Description**: Receive product prices in the store and calculate which option is best.

Here is an example where we compare a price in dollars against a "BCV Rate Price" (which is usually an amount that the business invents using the official rate).

Request Body (**JSON**):

```JSON
{
  "price_a": 20.00,
  "type_a": "USD",
  "price_b": 25.00,
  "type_b": "BCV_RATE",
  "target_currency": "USD",
  "preferred_source": "BINANCE"
}
```

<!-- TOC --><a name="what-would-this-look-like-in-practice"></a>
### What would this look like in practice?

Imagine that you are faced with two totally different situations on the same day:

<!-- TOC --><a name="case-1-compare-cash-vs-transfer-rate-of-the-day"></a>
#### Case 1: Compare cash vs. transfer (Rate of the day)
If you have dollars in cash and want to know if it is better for you to pay in bolivars by transfer:

```JSON
{
  "price_a": 50.00,
  "type_a": "USD",
  "price_b": 2100.00,
  "type_b": "VES",
  "preferred_source": "BCV"
}
```

<!-- TOC --><a name="case-2-the-trade-has-phantom-prices-at-the-bcv-rate"></a>
#### Case 2: The trade has "phantom" prices at the BCV rate

If the store tells you: "In dollars it is $20, but if you pay in bolivars I will calculate it at the BCV rate":

```JSON
{
  "price_a": 20.00,
  "type_a": "USD",
  "price_b": 20.00,
  "type_b": "BCV_RATE",
  "preferred_source": "BCV"
}
```

<!-- TOC --><a name="case-3-you-want-to-see-if-the-store-rate-beats-the-black-market-binance"></a>
#### Case 3: You want to see if the store rate beats the black market (Binance)
If the business offers you a price in bolivars that seems "cheap" and you want to see if you really beat the P2P market:

```JSON
{
  "price_a": 1000.00,
  "type_a": "VES",
  "price_b": 25.00,
  "type_b": "USD",
  "preferred_source": "BINANCE"
}
```
Finally, the
The response that the API will return (**JSON**) will be something like:

```JSON
{
  "request_summary": {
    "option_a": {"price": 20.00, "type": "USD"},
    "option_b": {"price": 25.00, "type": "BCV_RATE"},
    "source_used": "BCV",
    "target_currency": "USD"
  },
  "calculation_details": {
    "option_a_in_ves": 830.00,
    "option_b_in_ves": 1037.50,
    "exchange_rate_applied": 41.50
  },
  "recommendation": {
    "best_option": "OPTION_A",
    "savings_amount": 5.00,
    "savings_currency": "USD",
    "message": "Pagar en USD (a tasa de mercado) es más conveniente. Estás ahorrando 5.00 USD frente al precio fijado a tasa oficial del comercio."
  }
}
```

<!-- TOC --><a name="development-plan-2-week-schedule"></a>
## Development Plan (2 Week Schedule)

<!-- TOC --><a name="week-1-extraction-and-core-logic-pure-backend"></a>
#### Week 1: Extraction and Core Logic (Pure Backend) 

* Day 1-2: Setting up Python environment, installing dependencies, Git repositories and Docker files. 
 * Day 3-4: Development of app/scrapers.py. Create asynchronous functions to extract rates from **BCV** and Binance. 
 * Day 5-7: Connection with Upstash Redis. Save the data and structure the logic in services.py.

<!-- TOC --><a name="week-2-api-deployment-and-testing"></a>
####  Week 2: **API**, Deployment and Testing 

* Day 8-10: Creation of the endpoints in app/main.py. Test requests from Swagger (/docs). 
* Day 11-12: Setting up background tasks to keep Redis updated automatically. 
* Day 13-14: Construction of the final Docker image and deployment to production (Render, Koyeb or **VPS**). Load tests.

Local Configuration (Traditional Method)

<!-- TOC --><a name="clone-the-repository"></a>
### Clone the repository:

git clone https://github.com/watchtheblind/ahorrave-backend.git cd saveve-backend
<!-- TOC --><a name="create-and-initialize-the-virtual-environment"></a>
### Create and initialize the Virtual Environment: 
```shell 
python -m venv venv 
```

On Windows: ```.\venv\Scripts\activate ```

On Linux/Mac: ```source venv/bin/activate ```

<!-- TOC --><a name="install-dependencies"></a>
### Install dependencies: 
```shell 
pip install -r requirements.txt 
```

<!-- TOC --><a name="run-the-api-in-development-mode"></a>
### Run the API in development mode: 
```shell 
uvicorn app.main:app --reload
```

Local Configuration (Using Docker)

Using Docker makes it easy to run the project identically on any computer, without the need to manually configure Python or virtual environments.

Requirements: Have Docker and Docker Desktop (or Docker Compose) installed.

<!-- TOC --><a name="build-and-run-the-container"></a>
### Build and run the container: 

In the same folder where the docker-compose.yml file is located, run: 

```shell 
docker-compose up --build
```

This command will download the Python environment, install the dependencies, and run the **API**. If you want it to run in the background (freeing up your terminal), add the -d flag at the end: docker-compose up --build -d

<!-- TOC --><a name="stop-containers"></a>
### Stop containers:

If you ran the normal command, press Ctrl + C in your terminal. If you ran it in the background, run: docker-compose down

<!-- TOC --><a name="test-the-api-and-diagrams"></a>
### Test the **API** AND DIAGRAMS

Regardless of whether you used the traditional or Docker method, once the server is running, open your web browser and visit: [http://**127**.0.0.1:**8000**/docs](https://[www.google.com/search?q=http://**127**.0.0.1:**8000**/docs](https://www.google.com/search?q=http://**127**.0.0.1:**8000**/docs))

There you will find the Swagger graphical interface, where you can easily test all the routes and send test data to the calculator.

<!-- TOC --><a name="data-state-diagram"></a>
### Data State Diagram

Shows how the data life cycle works

![DIAGRAM1](http://i.imgur.com/HYE9C3K.png)

<!-- TOC --><a name="data-flow-diagram"></a>
### Data flow diagram

Shows how the application reacts to user interactions

![DIAGRAM2](https://i.imgur.com/UNouMBN.png)

<!-- TOC --><a name="data-model-diagram-redis"></a>
### Data Model Diagram (Redis)

This diagram shows how we will organize information within Redis so that it is efficient and easy to query.

![DIAGRAM3](https://i.imgur.com/3dX3L6O.png)

<!-- TOC --><a name="normalization-decision-diagram"></a>
### Normalization Decision Diagram

This is the "algorithm" that must be translated into code in the `services.py`. It is the golden rule for price normalization.

![DIAGRAM4](https://i.imgur.com/FTiyn5u.png)

<!-- TOC --><a name="production-deployment-guide-render-upstash"></a>
##  Production Deployment Guide (Render + Upstash)

This section documents the steps and decisions for implementing the API in the cloud for free.

<!-- TOC --><a name="1-database-upstash-redis"></a>
### 1. Database: Upstash Redis
- Create a free account at [upstash.com](https://upstash.com).
- Create a Redis database. The current free plan offers **500,000 commands per month** (enough for ~250,000 visits).
- **Important**: In the database configuration, disable "Auto Upgrade" to avoid unexpected costs if the limit is exceeded.

<!-- TOC --><a name="2-api-deployment-render"></a>
### 2. API deployment: Render
- The project is ready to be deployed in [render.com](https://render.com) using the `Dockerfile`.
- **Free plan**: The web service goes to sleep after 15 minutes of no activity**. To keep it active 24/7, use an external service like [cron-job.org](https://cron-job.org) ping the URL `/health` every 10 minutes.
- **Required environment variables** (configure in the Render panel):
  | Variable | Value | Mandatory |
  |----------|-------|-------------|
  | `APP_ENV` | `production` | Yes |
  | `UPSTASH_REDIS_REST_URL` | URL of your Upstash database | Yes |
  | `UPSTASH_REDIS_REST_TOKEN` | Token of your Upstash database | Yes |

<!-- TOC --><a name="3-solving-common-problems-in-production"></a>
### 3. Solving common problems in production

<!-- TOC --><a name="mistake-cannot-import-name-redis-from-upstash_redis"></a>
#### Mistake: `cannot import name 'Redis' from 'upstash_redis'`
**Cause**: The bookstore `upstash-redis` changed your API and the import fails in some environments.

**Solution**: The `database.py` current uses the standard library `redis` (with `import redis`) and configure the SSL connection manually. This solution is more stable.

<!-- TOC --><a name="mistake-error-upstash-usando-mockredis"></a>
#### Mistake: `Error Upstash: usando MockRedis`
**Cause**: Environment variables `APP_ENV=production`, `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are not configured or have incorrect values.

**Solution**: Verify in the Render panel that the variables exist and are correct. After correcting them, do a "Manual Deploy" so that they are applied.

<!-- TOC --><a name="4-local-development-without-upstash"></a>
### 4. Local Development (without Upstash)
For local development, **nothing needs to be configured**. Default, `APP_ENV=development` and the API will use `MockRedis` (in-memory cache). So any developer can clone and run `docker-compose up --build` without external dependencies.

<!-- TOC --><a name="5-future-updates"></a>
### 5. Future updates
Every time changes are uploaded to the branch `main` on GitHub, Render automatically rebuilds and deploys the new version. No manual intervention required.


<!-- TOC --><a name="-faq-technical-project-decisions"></a>
## ❓ FAQ: Technical Project Decisions

This document answers frequently asked questions about why we chose this technology stack for our currency calculator.

---

<!-- TOC --><a name="1-why-fastapi-and-not-another-framework-like-flask-or-django"></a>
### 1. Why FastAPI and not another framework like Flask or Django?
We chose **FastAPI** for three critical reasons for this project:
* **Speed ​​and Concurrency:** FastAPI is asynchronous. This allows our API to handle hundreds of requests at a time without blocking, which is vital if the app goes viral.
* **Automatic Documentation:** FastAPI gives us an interactive web page (in `/docs`) that serves as a technical manual. Anyone can see how the API works and test it without writing code.
* **Data Validation:** By simply defining what we expect to receive, FastAPI automatically rejects any poorly formatted data, avoiding human errors in the database.

<!-- TOC --><a name="2-why-do-we-need-redis-isnt-a-normal-database-enough"></a>
### 2. Why do we need Redis? Isn't a normal database enough?
Using a traditional database (such as PostgreSQL or MySQL) would be too slow for this use case.
* **Extreme Speed:** Redis saves data in RAM, not on the hard drive. The answer is in milliseconds.
* **Smart Cache:** Since exchange rates do not change every second, we save the scraper result in Redis. Thus, the user always receives an instant response and we do not overload external websites (BCV/Binance).
* **TTL (Time to Live):** Redis allows you to configure data to "self-destruct" or refresh after X amount of time, automating the updating of rates.

<!-- TOC --><a name="3-why-do-we-include-background-tasks"></a>
### 3. Why do we include "Background Tasks"?
This is the "third pillar" of our architecture.
* **User Independence:** When a user requests a calculation, we do not want their app to be "loading" while our API searches the BCV website. 
* **Fluid Flow:** Background tasks allow our API to take care of updating rates (the "dirty work") regardless of whether the user is currently viewing something.
* **Reliability:** If the BCV server is slow or goes down, our system does not fail; it just keeps serving the last rate saved in Redis.

<!-- TOC --><a name="4-is-this-level-of-complexity-really-necessary-for-something-so-small"></a>
### 4. Is this level of complexity really necessary for something so "small"?
* **The short answer is: Yes.** * What seems like a "simple calculator" becomes a **performance** problem when 100 people ask at the same time. By structuring it this way from day 1, we guarantee that the app is stable, professional and scalable. Additionally, we are using tools that are industry standard, which makes our code very maintainable.

<!-- TOC --><a name="5-how-do-scrapers-work"></a>
### 5. How do scrapers work?
Because prices are updated differently in terms of BCV and Binance rates, the logic is separated into these two processes for scrappers:

* #### BCV Worker:

1. Configure it as a scheduled task (cron-like) that runs strictly from 11:00 AM to 6:00 PM.

2. Store under a specific key in Redis (ex: rates:bcv).

* #### Binance Worker:

1. Set it with an interval of 10-15 minutes.

2. Store under a separate key (ex: rates:binance).

As Binance is an API, this worker will be much lighter and faster than the BCV worker.

