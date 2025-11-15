# producer.py - publica mensajes JSON durables a un exchange 'weather_exchange'


import os
import json
import time
import logging
import random
import pika


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
INTERVAL = int(os.environ.get('PRODUCER_INTERVAL_SEC', '5'))


EXCHANGE = 'weather_exchange'
ROUTING_KEY = 'station.reading'


# Mensaje de ejemplo con campos: station_id, ts, temperature, humidity, wind_speed


def random_reading(station_id: str):
return {
'station_id': station_id,
'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
'temperature': round(random.uniform(-10, 40), 2),
'humidity': round(random.uniform(0, 100), 2),
'wind_speed': round(random.uniform(0, 30), 2)
}




def main():
params = pika.URLParameters(RABBITMQ_URL)
# reconexión simple con reintentos
while True:
try:
conn = pika.BlockingConnection(params)
channel = conn.channel()
channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)


station_ids = ['station-A', 'station-B', 'station-C']
logging.info('Producer connected to RabbitMQ, sending messages every %s seconds', INTERVAL)


while True:
msg = random_reading(random.choice(station_ids))
body = json.dumps(msg)
properties = pika.BasicProperties(delivery_mode=2, content_type='application/json')
channel.basic_publish(exchange=EXCHANGE, routing_key=ROUTING_KEY, body=body, properties=properties)
logging.info('Published message: %s', body)
time.sleep(INTERVAL)


except Exception as e:
logging.exception('Producer connection failed, retrying in 5s: %s', e)
time.sleep(5)




if __name__ == '__main__':
main()