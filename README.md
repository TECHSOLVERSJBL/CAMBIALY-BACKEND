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

## Plan de Desarrollo (Cronograma de 2 Semanas)

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

### Probar la **API** Y DIAGRAMAS

Sin importar si usaste el método tradicional o Docker, una vez que el servidor esté corriendo, abre tu navegador web y visita: [http://**127**.0.0.1:**8000**/docs](https://[www.google.com/search?q=http://**127**.0.0.1:**8000**/docs](https://www.google.com/search?q=http://**127**.0.0.1:**8000**/docs))

Allí encontrarás la interfaz gráfica de Swagger, donde podrás probar todas las rutas y enviar datos de prueba a la calculadora fácilmente.


![DIAGRAMA1](https://i.imgur.com/FxltGeZ.png)
![DIAGRAMA2](https://i.imgur.com/hnYeE1E.png)

## ❓ FAQ: Decisiones Técnicas del Proyecto

Este documento responde a las dudas frecuentes sobre por qué elegimos este stack tecnológico para nuestra calculadora de divisas.

---

### 1. ¿Por qué FastAPI y no otro framework como Flask o Django?
Elegimos **FastAPI** por tres razones críticas para este proyecto:
* **Velocidad y Concurrencia:** FastAPI es asíncrono. Esto permite que nuestra API maneje cientos de peticiones a la vez sin bloquearse, algo vital si la app se hace viral.
* **Documentación Automática:** FastAPI nos da una página web interactiva (en `/docs`) que sirve como manual técnico. Cualquier persona puede ver cómo funciona la API y probarla sin escribir código.
* **Validación de Datos:** Con solo definir qué esperamos recibir, FastAPI rechaza automáticamente cualquier dato mal formateado, evitándonos errores humanos en la base de datos.

### 2. ¿Por qué necesitamos Redis? ¿No basta con una base de datos normal?
Usar una base de datos tradicional (como PostgreSQL o MySQL) sería demasiado lento para este caso de uso.
* **Velocidad Extrema:** Redis guarda los datos en la memoria RAM, no en el disco duro. La respuesta es en milisegundos.
* **Caché Inteligente:** Como las tasas de cambio no cambian cada segundo, guardamos el resultado del scraper en Redis. Así, el usuario siempre recibe una respuesta instantánea y nosotros no sobrecargamos las webs externas (BCV/Binance).
* **TTL (Time to Live):** Redis permite configurar que un dato se "autodestruya" o refresque tras X tiempo, automatizando la actualización de las tasas.

### 3. ¿Por qué incluimos "Tareas en Segundo Plano" (Background Tasks)?
Este es el "tercer pilar" de nuestra arquitectura.
* **Independencia del Usuario:** Cuando un usuario pide un cálculo, no queremos que su app se quede "cargando" mientras nuestra API busca en la web del BCV. 
* **Flujo Fluido:** Las tareas en segundo plano permiten que nuestra API se encargue de actualizar las tasas (el "trabajo sucio") independientemente de si el usuario está consultando algo en ese momento.
* **Fiabilidad:** Si el servidor del BCV está lento o se cae, nuestro sistema no falla; simplemente sigue entregando la última tasa guardada en Redis.

### 4. ¿Es realmente necesario este nivel de complejidad para algo tan "pequeño"?
* **La respuesta corta es: Sí.** * Lo que parece una "calculadora simple" se convierte en un problema de **rendimiento** cuando 100 personas preguntan al mismo tiempo. Al estructurarlo así desde el día 1, garantizamos que la app sea estable, profesional y escalable. Además, estamos usando herramientas que son estándar en la industria, lo que hace que nuestro código sea muy fácil de mantener.
