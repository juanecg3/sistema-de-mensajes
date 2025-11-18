
#  **README.md – Sistema de Gestión de Logs de Estaciones Meteorológicas**

Este proyecto implementa un **sistema distribuido de ingestión, validación y persistencia de datos meteorológicos** usando microservicios en Python, RabbitMQ, PostgreSQL y Docker.
Está diseñado para ser **escalable, tolerante a fallos, extensible** y fácil de administrar.

---

#  **Arquitectura del Sistema**

```
 ┌──────────────┐       ┌───────────────┐        ┌───────────────────────┐
 │  Producers   │ ----> │   RabbitMQ    │ -----> │      Consumer          │
 │ (Python)     │       │  Exchange +   │        │ (Valida + Inserta en   │
 │ Envía JSON   │       │   Queue       │        │     PostgreSQL)        │
 └──────────────┘       └───────────────┘        └──────────┬────────────┘
                                                            ▼
                                                  ┌──────────────────────┐
                                                  │     PostgreSQL        │
                                                  │  weather_logs,        │
                                                  │  weather_deadletters  │
                                                  └──────────────────────┘
```

---

#  **Tecnologías utilizadas**

| Componente         | Tecnología                                   |
| ------------------ | -------------------------------------------- |
| Broker de Mensajes | RabbitMQ 3.13 (con plugin de administración) |
| Base de Datos      | PostgreSQL 16                                |
| Productor          | Python 3.13 + Pika                           |
| Consumidor         | Python 3.13 + Pika + psycopg + Prometheus    |
| Orquestación       | Docker & Docker Compose                      |
| Monitoreo          | Prometheus client para métricas del consumer |

---

#  **Estructura del repositorio**

```
/
├── consumer/
│   ├── consumer.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── producer/
│   ├── producer.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── db/
│   └── init.sql
│
├── docker-compose.yml
└── README.md
```

---

#  **Instalación y Ejecución**

## 1. Requisitos previos

* Docker Desktop o Docker Engine
* Docker Compose v2
* Git

---

## 2. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/sistema-de-mensajes.git
cd sistema-de-mensajes
```

---

## 3. Levantar toda la plataforma

```bash
docker compose up --build
```

La primera vez tarda más porque se instalan dependencias y se generan volúmenes.

---

#  **Componentes**

---

#  1. RabbitMQ

Dashboard web:

```
http://localhost:15672
```

Credenciales por defecto:

```
user: guest
pass: guest
```

---

#  2. PostgreSQL

Conexión para psql:

```bash
docker exec -it postgres psql -U weather weatherdb
```

Tablas creadas en `init.sql`:

* **weather_logs** — registros válidos
* **weather_deadletters** — mensajes rechazados por validación

---

#  3. Producer 

Genera un JSON cada 5 segundos:

Ejemplo:

```json
{
  "station_id": "station-A",
  "ts": "2025-11-15T19:00:00Z",
  "temperature": 25.4,
  "humidity": 57.8,
  "wind_speed": 12.3
}
```

Envía mensajes durables hacia:

* Exchange: `weather_exchange`
* Routing Key: `station.reading`
* Queue: `weather_queue`

---

#  4. Consumer (Consumidor)

Funciones principales:

✔ Procesamiento con `prefetch_count=1`
✔ Validación de rangos (temperatura, humedad, viento)
✔ Inserción en PostgreSQL
✔ Deadletters en caso de error
✔ Exposición de métricas Prometheus

Endpoint de métricas:

```
http://localhost:8000
```

---

#  **Métricas disponibles**

* `weather_messages_processed_total`
* `weather_messages_failed_total`
* `weather_message_processing_seconds`

Estas métricas permiten integrar fácilmente **Prometheus + Grafana**.

---

#  **Validación de Datos**

El consumidor valida:

| Campo       | Rango           |
| ----------- | --------------- |
| temperature | -80 a 60 grados |
| humidity    | 0 a 100 %       |
| wind_speed  | 0 a 200 km/h    |

Si algún valor está fuera de rango:

* El mensaje se rechaza (`basic_reject`)
* Se guarda en **weather_deadletters**
* Se incrementa `weather_messages_failed_total`

---

#  **Persistencia**

El sistema usa volúmenes Docker:

```
postgres_data
rabbitmq_data
```

Esto asegura que:

* La BD no se borra al detener contenedores
* RabbitMQ persiste colas y mensajes durables

---

#  **Comandos útiles**

## Reconstruir todo:

```bash
docker compose up --build
```

## Detener y limpiar contenedores (pero NO borrar datos):

```bash
docker compose down
```

## Borrar volúmenes ( borra base de datos y cola):

```bash
docker compose down -v
```

---

#  **Próximas mejoras **

* API REST para consulta de registros (FastAPI o Flask)
* Dashboards en Grafana para visualización en tiempo real
* Módulo de alertas (notificaciones si una estación supera umbrales)
* Nuevos productores simulando múltiples estaciones en paralelo
* Escalamiento horizontal de consumers

---

