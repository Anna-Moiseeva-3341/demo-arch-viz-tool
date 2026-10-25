import os
import time

import json
import httpx
import pika
from pika.exceptions import AMQPConnectionError

AMQP_URL = os.getenv("AMQP_URL")
EMAIL_API_URL = os.getenv("EMAIL_API_URL")

def on_message(channel, method, properties, body):
    event = json.loads(body)
    print(f"ID брони [{event['hold_id']}]: книга {event['title']}, отправляется уведомление")
    try:
        httpx.post(f"{EMAIL_API_URL}/send", 
            json={"user_id": event["user_id"], "text": f"Забронирована книга {event['title']}"},
            timeout=2)
    except httpx.HTTPError:
        print("Почтовый сервис недоступен")

def connect():
    while True:
        try:
            return pika.BlockingConnection(pika.URLParameters(AMQP_URL))
        except AMQPConnectionError:
            print("Брокер не готов")
            time.sleep(2)

def main():
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue="hold_created", durable=True)
    channel.basic_consume(queue="hold_created", on_message_callback=on_message, auto_ack=True)
    print("Ожидание hold_created")
    channel.start_consuming()

if __name__ == "__main__":
    main()