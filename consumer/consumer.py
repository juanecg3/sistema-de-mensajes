# consumer.py - consume mensajes, valida, persiste en Postgres y expone métricas Prometheus
# Validaciones
errors = []
if temp is None or not (TEMP_MIN <= float(temp) <= TEMP_MAX):
errors.append(f'temperature out of range: {temp}')
if hum is None or not (HUM_MIN <= float(hum) <= HUM_MAX):
errors.append(f'humidity out of range: {hum}')
if wind is None or not (WIND_MIN <= float(wind) <= WIND_MAX):
errors.append(f'wind_speed out of range: {wind}')


cur = db_conn.cursor()
if errors:
reason = '; '.join(errors)
logging.warning('Validation failed for station %s: %s', station_id, reason)
cur.execute("INSERT INTO weather_deadletters (raw, reason) VALUES (%s, %s)", (Json(data), reason))
MSG_FAILED.inc()
return False


# Inserta en weather_logs
cur.execute(
"""
INSERT INTO weather_logs (station_id, ts, temperature, humidity, wind_speed, raw, status)
VALUES (%s, %s, %s, %s, %s, %s, %s)
""",
(station_id, ts, temp, hum, wind, Json(data), 'ok')
)
MSG_PROCESSED.inc()
logging.info('Inserted reading for station %s at %s', station_id, ts)
return True


except Exception as e:
logging.exception('Processing error: %s', e)
MSG_FAILED.inc()
# In production: send to DLX or alerting system
cur = db_conn.cursor()
cur.execute("INSERT INTO weather_deadletters (raw, reason) VALUES (%s, %s)", (Json({'error':'exception','payload': body}), str(e)))
return False




def main():
# Start Prometheus metrics server
start_http_server(METRICS_PORT)
logging.info('Prometheus metrics available on port %s', METRICS_PORT)


db_conn = connect_db()


params = pika.URLParameters(RABBITMQ_URL)
while not stop_event.is_set():
try:
conn = pika.BlockingConnection(params)
channel = conn.channel()
channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)


# Queue durable, bind to exchange, prefetch = 1
channel.queue_declare(queue=QUEUE_NAME, durable=True, arguments={
# ejemplo DLX: 'x-dead-letter-exchange': 'weather_dlx'
})
channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=ROUTING_KEY)
channel.basic_qos(prefetch_count=1)


logging.info('Consumer connected and waiting for messages...')


def on_message(ch, method, properties, body):
logging.info('Received message: %s', body)
ok = process_message(body, db_conn)
if ok:
ch.basic_ack(delivery_tag=method.delivery_tag)
else:
# No ack; send to