# AHORRAVE
<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [**API** Calculadora de Conveniencia Cambiaria (**VES**/**USD**/**EUR**)](#api-calculadora-de-conveniencia-cambiaria-vesusdeur)
- [🏗️ Arquitectura del Sistema](#-arquitectura-del-sistema)
- [📁 Estructura de carpetas ](#-estructura-de-carpetas)
   * [Descripción rápida:](#descripción-rápida)
   * [Consideraciones acerca de la estructura](#consideraciones-acerca-de-la-estructura)
- [🛠️ Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [🔌 Endpoints de la API (Rutas)](#-endpoints-de-la-api-rutas)
   * [**1. Obtener Tasas del Día BCV**](#1-obtener-tasas-del-día-bcv)
   * [**2. Obtener Tasas del Día Binance**](#2-obtener-tasas-del-día-binance)
   * [2. Calcular Conveniencia](#2-calcular-conveniencia)
   * [¿Cómo se vería esto en la práctica?](#cómo-se-vería-esto-en-la-práctica)
      + [Caso 1: Comparar efectivo vs. transferencia (Tasa del día)](#caso-1-comparar-efectivo-vs-transferencia-tasa-del-día)
      + [Caso 2: El comercio tiene precios "fantasma" a tasa BCV](#caso-2-el-comercio-tiene-precios-fantasma-a-tasa-bcv)
      + [Caso 3: Quieres ver si la tasa de la tienda le gana al mercado negro (Binance)](#caso-3-quieres-ver-si-la-tasa-de-la-tienda-le-gana-al-mercado-negro-binance)
- [Plan de Desarrollo (Cronograma de 2 Semanas)](#plan-de-desarrollo-cronograma-de-2-semanas)
      + [Semana 1: Extracción y Lógica Central (Backend Puro) ](#semana-1-extracción-y-lógica-central-backend-puro)
      + [Semana 2: **API**, Despliegue y Pruebas ](#semana-2-api-despliegue-y-pruebas)
   * [Clonar el repositorio:](#clonar-el-repositorio)
   * [Crear e inicializar el Entorno Virtual: ](#crear-e-inicializar-el-entorno-virtual)
   * [Instalar dependencias: ](#instalar-dependencias)
   * [Correr la API en modo desarrollo: ](#correr-la-api-en-modo-desarrollo)
   * [Construir y ejecutar el contenedor: ](#construir-y-ejecutar-el-contenedor)
   * [Detener los contenedores:](#detener-los-contenedores)
   * [Probar la **API** Y DIAGRAMAS](#probar-la-api-y-diagramas)
   * [Diagrama de estado de datos](#diagrama-de-estado-de-datos)
   * [Diagrama de flujo de datos](#diagrama-de-flujo-de-datos)
   * [Diagrama de Modelo de Datos (Redis)](#diagrama-de-modelo-de-datos-redis)
   * [Diagrama de Decisión de Normalización](#diagrama-de-decisión-de-normalización)
- [❓ FAQ: Decisiones Técnicas del Proyecto](#-faq-decisiones-técnicas-del-proyecto)
   * [1. ¿Por qué FastAPI y no otro framework como Flask o Django?](#1-por-qué-fastapi-y-no-otro-framework-como-flask-o-django)
   * [2. ¿Por qué necesitamos Redis? ¿No basta con una base de datos normal?](#2-por-qué-necesitamos-redis-no-basta-con-una-base-de-datos-normal)
   * [3. ¿Por qué incluimos "Tareas en Segundo Plano" (Background Tasks)?](#3-por-qué-incluimos-tareas-en-segundo-plano-background-tasks)
   * [4. ¿Es realmente necesario este nivel de complejidad para algo tan "pequeño"?](#4-es-realmente-necesario-este-nivel-de-complejidad-para-algo-tan-pequeño)
   * [5. Cómo funcionan los scrapers?](#5-cómo-funcionan-los-scrapers)


<!-- TOC end -->
<!-- TOC --><a name="api-calculadora-de-conveniencia-cambiaria-vesusdeur"></a>
## **API** Calculadora de Conveniencia Cambiaria (**VES**/**USD**/**EUR**)

Este proyecto consiste en una **API** **REST** automatizada y de alta velocidad diseñada para calcular en tiempo real qué método de pago (divisas en efectivo o bolívares a tasa oficial/paralela) resulta más conveniente al realizar una compra en Venezuela.

El objetivo es resolver un problema cotidiano: la pérdida de dinero por redondeos mal calculados o brechas cambiarias entre comercios y tasas oficiales.

<!-- TOC --><a name="-arquitectura-del-sistema"></a>
## 🏗️ Arquitectura del Sistema

Para soportar un alto tráfico de usuarios sin saturar los servidores ni ser bloqueados por las páginas de origen, el backend no consulta el BCV ni Binance en cada cálculo. En su lugar, utiliza un patrón de **Caché**:

1. **El Recolector (Scraper/API Worker):** Un script asíncrono se ejecuta en segundo plano cada ciertas horas. Visita la página del BCV, extrae las tasas del Dólar y Euro, y consulta la API de Binance.
2. **La Memoria Rápida (Redis Caché):** El recolector guarda las tasas del día en una base de datos en memoria (Redis). Leer de aquí toma menos de 2 milisegundos.
3. **El Motor (FastAPI):** Cuando un usuario ingresa montos a la calculadora, FastAPI toma las tasas guardadas en Redis, realiza la matemática al instante y devuelve la recomendación de compra.

<!-- TOC --><a name="-estructura-de-carpetas"></a>
## 📁 Estructura de carpetas 

Para mantener el orden, la escalabilidad y la claridad, se estructuran los archivos de la siguiente manera:

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

<!-- TOC --><a name="descripción-rápida"></a>
### Descripción rápida:

* **`app/main.py`**: Aquí es donde definimos las rutas (`/api/v1/rates/bcv`, `/api/v1/rates/binance` y `/api/v1/calcular`). Solo delega el trabajo a los otros archivos.
* **`app/schemas.py`**: Es el "contrato" de la API. Aquí definimos los JSONs que vimos antes (`CalculationRequest`, `CalculationResponse`). Si los datos no vienen como esperamos, FastAPI fallará aquí antes de llegar a la lógica.
* **`app/services.py`**: Aquí reside el **diagrama de decisión de normalización**. Es donde la magia ocurre: recibes los datos del esquema, consultas Redis, normalizas a `VES` y comparas.
* **`app/scrapers.py`**: Tendrá dos funciones principales (ej: `update_bcv_rates` y `update_binance_rates`). Cada una será una tarea asíncrona que el sistema llamará según su propia frecuencia.
* **`app/database.py`**: Manejo de la conexión con `redis-py`. Mantiene el código de conexión limpio y reutilizable.

<!-- TOC --><a name="consideraciones-acerca-de-la-estructura"></a>
### Consideraciones acerca de la estructura

1. **Escalabilidad:** Si mañana quieres añadir un tercer scraper (por ejemplo, para el Euro o tasas de otra web), solo creas la función en `scrapers.py` y añades una ruta en `main.py`.
2. **Mantenibilidad:** Si hay un error matemático en el cálculo, sabes que está en `services.py`. Si los datos se están obteniendo mal, sabes que está en `scrapers.py`.
3. **Testing:** Al separar la lógica (`services.py`) de la web (`main.py`), puedes hacer pruebas unitarias sin tener que levantar un servidor web.


---

<!-- TOC --><a name="-tecnologías-utilizadas"></a>
## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.10+
* **Framework Web:** `FastAPI` (Asíncrono, ultrarápido y genera documentación automática).
* **Extracción de Datos:** `HTTPX` (Peticiones HTTP asíncronas) y `BeautifulSoup4` (Web Scraping para el BCV).
* **Caché y Base de Datos:** `Redis` (Almacenamiento temporal ultraveloz en la nube vía Upstash).
* **Servidor de Producción:** `Uvicorn`.
* **Contenedores**: `Docker` y `Docker Compose` (Para empaquetar y ejecutar la aplicación en cualquier entorno de forma estandarizada).


<!-- TOC --><a name="-endpoints-de-la-api-rutas"></a>
## 🔌 Endpoints de la API (Rutas)
La API expondrá principalmente dos rutas que el Frontend o la App móvil consumirán:

<!-- TOC --><a name="1-obtener-tasas-del-día-bcv"></a>
### **1. Obtener Tasas del Día BCV**

Ruta: `GET /api/v1/rates/bcv`

**Descripción**: Retorna las tasas oficiales (USD/EUR) del Banco Central de Venezuela.

**Propósito**: Retorna las tasas oficiales (USD/EUR) del Banco Central de Venezuela.

**Frecuencia**: Actualización mediante tarea programada (cron) de 11:00 AM a 6:00 PM.

**Almacenamiento**: clave `rates: bcv` en Redis.

Resultado de la petición (**JSON**): 

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
<!-- TOC --><a name="2-obtener-tasas-del-día-binance"></a>
### **2. Obtener Tasas del Día Binance**

Ruta: `GET /api/v1/rates/bcv`

**Descripción**: Retorna la tasa P2P de Binance

**Propósito**: Actualización constante cada 10-15 minutos debido a la alta volatilidad.

**Frecuencia**: Actualización mediante tarea programada (cron) de 11:00 AM a 6:00 PM.

**Almacenamiento**: clave `rates: binance` en Redis.

Resultado de la petición (**JSON**): 

```JSON
{
  "source": "Binance P2P",
  "last_updated": "2026-05-29T15:35:00Z",
  "rates": {
    "USD": 45.20
  }
}
```

<!-- TOC --><a name="2-calcular-conveniencia"></a>
### 2. Calcular Conveniencia

Ruta: `POST /api/v1/calcular`

**Descripción**: Recibe los precios del producto en la tienda y calcula cuál opción es mejor.

Aquí un ejemplo donde comparamos un precio en dólares contra un "Precio Tasa BCV" (que suele ser un monto que el comercio inventa usando la tasa oficial).

Cuerpo de la Petición (**JSON**):

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

<!-- TOC --><a name="cómo-se-vería-esto-en-la-práctica"></a>
### ¿Cómo se vería esto en la práctica?

Imagina que estás frente a dos situaciones totalmente distintas en el mismo día:

<!-- TOC --><a name="caso-1-comparar-efectivo-vs-transferencia-tasa-del-día"></a>
#### Caso 1: Comparar efectivo vs. transferencia (Tasa del día)
Si tienes dólares en efectivo y quieres saber si te conviene pagar en bolívares por transferencia:

```JSON
{
  "price_a": 50.00,
  "type_a": "USD",
  "price_b": 2100.00,
  "type_b": "VES",
  "preferred_source": "BCV"
}
```

<!-- TOC --><a name="caso-2-el-comercio-tiene-precios-fantasma-a-tasa-bcv"></a>
#### Caso 2: El comercio tiene precios "fantasma" a tasa BCV

Si la tienda te dice: "En dólares son 20$, pero si pagas en bolívares te lo calculo a tasa BCV":

```JSON
{
  "price_a": 20.00,
  "type_a": "USD",
  "price_b": 20.00,
  "type_b": "BCV_RATE",
  "preferred_source": "BCV"
}
```

<!-- TOC --><a name="caso-3-quieres-ver-si-la-tasa-de-la-tienda-le-gana-al-mercado-negro-binance"></a>
#### Caso 3: Quieres ver si la tasa de la tienda le gana al mercado negro (Binance)
Si el comercio te ofrece un precio en bolívares que parece "barato" y quieres ver si realmente le ganas al mercado P2P:

```JSON
{
  "price_a": 1000.00,
  "type_a": "VES",
  "price_b": 25.00,
  "type_b": "USD",
  "preferred_source": "BINANCE"
}
```
Finalmente, la
Respuesta que la API devolverá (**JSON**) será algo como:

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

<!-- TOC --><a name="plan-de-desarrollo-cronograma-de-2-semanas"></a>
## Plan de Desarrollo (Cronograma de 2 Semanas)

<!-- TOC --><a name="semana-1-extracción-y-lógica-central-backend-puro"></a>
#### Semana 1: Extracción y Lógica Central (Backend Puro) 

* Día 1-2: Configuración del entorno de Python, instalación de dependencias, repositorios Git y archivos de Docker. 
 * Día 3-4: Desarrollo de app/scrapers.py. Crear funciones asíncronas para extraer tasas de **BCV** y Binance. 
 * Día 5-7: Conexión con Upstash Redis. Guardar los datos y estructurar la lógica en services.py.

<!-- TOC --><a name="semana-2-api-despliegue-y-pruebas"></a>
####  Semana 2: **API**, Despliegue y Pruebas 

* Día 8-10: Creación de los endpoints en app/main.py. Probar los requests desde Swagger (/docs). 
* Día 11-12: Configuración de tareas en segundo plano para mantener Redis actualizado automáticamente. 
* Día 13-14: Construcción de la imagen Docker final y despliegue en producción (Render, Koyeb o **VPS**). Pruebas de carga.

Configuración Local (Método Tradicional)

<!-- TOC --><a name="clonar-el-repositorio"></a>
### Clonar el repositorio:

git clone https://github.com/watchtheblind/ahorrave-backend.git cd ahorrave-backend
<!-- TOC --><a name="crear-e-inicializar-el-entorno-virtual"></a>
### Crear e inicializar el Entorno Virtual: 
```shell 
python -m venv venv 
```

En Windows: ```.\venv\Scripts\activate ```

En Linux/Mac: ```source venv/bin/activate ```

<!-- TOC --><a name="instalar-dependencias"></a>
### Instalar dependencias: 
```shell 
pip install -r requirements.txt 
```

<!-- TOC --><a name="correr-la-api-en-modo-desarrollo"></a>
### Correr la API en modo desarrollo: 
```shell 
uvicorn app.main:app --reload
```

Configuración Local (Usando Docker)

Usar Docker facilita ejecutar el proyecto de forma idéntica en cualquier computadora, sin necesidad de configurar Python ni entornos virtuales manualmente.

Requisitos: Tener Docker y Docker Desktop (o Docker Compose) instalado.

<!-- TOC --><a name="construir-y-ejecutar-el-contenedor"></a>
### Construir y ejecutar el contenedor: 

En la misma carpeta donde se encuentra el archivo docker-compose.yml, ejecuta: 

```shell 
docker-compose up --build
```

Este comando descargará el entorno de Python, instalará las dependencias y ejecutará la **API**. Si deseas que corra en segundo plano (liberando tu terminal), añade la bandera -d al final: docker-compose up --build -d

<!-- TOC --><a name="detener-los-contenedores"></a>
### Detener los contenedores:

Si ejecutaste el comando normal, presiona Ctrl + C en tu terminal. Si lo corriste en segundo plano, ejecuta: docker-compose down

<!-- TOC --><a name="probar-la-api-y-diagramas"></a>
### Probar la **API** Y DIAGRAMAS

Sin importar si usaste el método tradicional o Docker, una vez que el servidor esté corriendo, abre tu navegador web y visita: [http://**127**.0.0.1:**8000**/docs](https://[www.google.com/search?q=http://**127**.0.0.1:**8000**/docs](https://www.google.com/search?q=http://**127**.0.0.1:**8000**/docs))

Allí encontrarás la interfaz gráfica de Swagger, donde podrás probar todas las rutas y enviar datos de prueba a la calculadora fácilmente.

<!-- TOC --><a name="diagrama-de-estado-de-datos"></a>
### Diagrama de estado de datos

Muestra cómo actúa el ciclo de vida de los datos

![DIAGRAMA1](http://i.imgur.com/HYE9C3K.png)

<!-- TOC --><a name="diagrama-de-flujo-de-datos"></a>
### Diagrama de flujo de datos

Muestra como actúa la aplicación ante las interacciones del usuario

![DIAGRAMA2](https://i.imgur.com/UNouMBN.png)

<!-- TOC --><a name="diagrama-de-modelo-de-datos-redis"></a>
### Diagrama de Modelo de Datos (Redis)

Este diagrama muestra cómo organizaremos la información dentro de Redis para que sea eficiente y fácil de consultar.

![DIAGRAMA3](https://i.imgur.com/3dX3L6O.png)

<!-- TOC --><a name="diagrama-de-decisión-de-normalización"></a>
### Diagrama de Decisión de Normalización

Este es el "algoritmo" que se debe traducir a código en el `services.py`. Es la regla de oro para la normalización de precios.

![DIAGRAMA4](https://i.imgur.com/FTiyn5u.png)


<!-- TOC --><a name="-faq-decisiones-técnicas-del-proyecto"></a>
## ❓ FAQ: Decisiones Técnicas del Proyecto

Este documento responde a las dudas frecuentes sobre por qué elegimos este stack tecnológico para nuestra calculadora de divisas.

---

<!-- TOC --><a name="1-por-qué-fastapi-y-no-otro-framework-como-flask-o-django"></a>
### 1. ¿Por qué FastAPI y no otro framework como Flask o Django?
Elegimos **FastAPI** por tres razones críticas para este proyecto:
* **Velocidad y Concurrencia:** FastAPI es asíncrono. Esto permite que nuestra API maneje cientos de peticiones a la vez sin bloquearse, algo vital si la app se hace viral.
* **Documentación Automática:** FastAPI nos da una página web interactiva (en `/docs`) que sirve como manual técnico. Cualquier persona puede ver cómo funciona la API y probarla sin escribir código.
* **Validación de Datos:** Con solo definir qué esperamos recibir, FastAPI rechaza automáticamente cualquier dato mal formateado, evitándonos errores humanos en la base de datos.

<!-- TOC --><a name="2-por-qué-necesitamos-redis-no-basta-con-una-base-de-datos-normal"></a>
### 2. ¿Por qué necesitamos Redis? ¿No basta con una base de datos normal?
Usar una base de datos tradicional (como PostgreSQL o MySQL) sería demasiado lento para este caso de uso.
* **Velocidad Extrema:** Redis guarda los datos en la memoria RAM, no en el disco duro. La respuesta es en milisegundos.
* **Caché Inteligente:** Como las tasas de cambio no cambian cada segundo, guardamos el resultado del scraper en Redis. Así, el usuario siempre recibe una respuesta instantánea y nosotros no sobrecargamos las webs externas (BCV/Binance).
* **TTL (Time to Live):** Redis permite configurar que un dato se "autodestruya" o refresque tras X tiempo, automatizando la actualización de las tasas.

<!-- TOC --><a name="3-por-qué-incluimos-tareas-en-segundo-plano-background-tasks"></a>
### 3. ¿Por qué incluimos "Tareas en Segundo Plano" (Background Tasks)?
Este es el "tercer pilar" de nuestra arquitectura.
* **Independencia del Usuario:** Cuando un usuario pide un cálculo, no queremos que su app se quede "cargando" mientras nuestra API busca en la web del BCV. 
* **Flujo Fluido:** Las tareas en segundo plano permiten que nuestra API se encargue de actualizar las tasas (el "trabajo sucio") independientemente de si el usuario está consultando algo en ese momento.
* **Fiabilidad:** Si el servidor del BCV está lento o se cae, nuestro sistema no falla; simplemente sigue entregando la última tasa guardada en Redis.

<!-- TOC --><a name="4-es-realmente-necesario-este-nivel-de-complejidad-para-algo-tan-pequeño"></a>
### 4. ¿Es realmente necesario este nivel de complejidad para algo tan "pequeño"?
* **La respuesta corta es: Sí.** * Lo que parece una "calculadora simple" se convierte en un problema de **rendimiento** cuando 100 personas preguntan al mismo tiempo. Al estructurarlo así desde el día 1, garantizamos que la app sea estable, profesional y escalable. Además, estamos usando herramientas que son estándar en la industria, lo que hace que nuestro código sea muy fácil de mantener.

<!-- TOC --><a name="5-cómo-funcionan-los-scrapers"></a>
### 5. Cómo funcionan los scrapers?
A causa de que los precios se actualizan de forma distinta en cuanto a tasas BCV y Binance se refiere, se separa la lógica en estos dos procesos para los scrappers:

* #### BCV Worker:

1. Configurarlo como una tarea programada (cron-like) que se ejecute estrictamente de 11:00 AM a 6:00 PM.

2. Almacenar bajo una llave específica en Redis (ej: rates:bcv).

* #### Binance Worker:

1. Configurarlo con un intervalo de 10-15 minutos.

2. Almacenar bajo una llave separada (ej: rates:binance).

Como Binance es una API, este worker será mucho más ligero y rápido que el del BCV.
