#!/usr/bin/env python3

import os
import json
import logging
import time
import signal
from threading import Event

import pika
import psycopg
from psycopg.rows import dict_row
from prometheus_client import start_http_server, Counter, Histogram

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

RABBITMQ_URL = os.environ.get("RABBITMQ_URL")
QUEUE_NAME = "weather_queue"
EXCHANGE = "weather_exchange"
ROUTING_KEY = "station.reading"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

METRICS_PORT = 8000

MSG_PROCESSED = Counter("weather_messages_processed_total", "Total processed messages")
MSG_FAILED = Counter("weather_messages_failed_total", "Total failed messages")
PROCESS_TIME = Histogram("weather_message_processing_seconds", "Time spent processing a message")

stop_event = Event()

TEMP_MIN, TEMP_MAX = -80.0, 60.0
HUM_MIN, HUM_MAX = 0.0, 100.0
WIND_MIN, WIND_MAX = 0.0, 200.0


def connect_db():
    logging.info("Connecting to PostgreSQL...")
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    logging.info("Connected to PostgreSQL")
    return conn


def process_message(body, db_conn):
    with PROCESS_TIME.time():
        try:
            data = json.loads(body)
            station_id = data.get("station_id")
            ts = data.get("ts")
            temp = data.get("temperature")
            hum = data.get("humidity")
            wind = data.get("wind_speed")

            errors = []

            if temp is None or not (TEMP_MIN <= float(temp) <= TEMP_MAX):
                errors.append(f"temperature out of range: {temp}")

            if hum is None or not (HUM_MIN <= float(hum) <= HUM_MAX):
                errors.append(f"humidity out of range: {hum}")

            if wind is None or not (WIND_MIN <= float(wind) <= WIND_MAX):
                errors.append(f"wind_speed out of range: {wind}")

            cur = db_conn.cursor()

            if errors:
                reason = "; ".join(errors)
                logging.warning("Validation failed: %s", reason)
                cur.execute(
                    "INSERT INTO weather_deadletters (raw, reason) VALUES (%s, %s)",
                    (json.dumps(data), reason),
                )
                return False

            cur.execute(
                """
                INSERT INTO weather_logs (station_id, ts, temperature, humidity, wind_speed, raw, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'ok')
                """,
                (station_id, ts, temp, hum, wind, json.dumps(data)),
            )

            logging.info("Stored reading from station %s", station_id)
            return True

        except Exception as e:
            logging.exception("Error processing message: %s", e)
            MSG_FAILED.inc()
            return False


def main():
    start_http_server(METRICS_PORT)
    logging.info(f"Prometheus metrics on port {METRICS_PORT}")

    db_conn = connect_db()

    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=ROUTING_KEY)
    channel.basic_qos(prefetch_count=1)

    logging.info("Consumer ready and waiting for messages")

    def callback(ch, method, properties, body):
        ok = process_message(body, db_conn)
        MSG_PROCESSED.inc() if ok else MSG_FAILED.inc()

        if ok:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()


if __name__ == "__main__":
    main()
