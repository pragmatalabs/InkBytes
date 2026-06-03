# rabbitmq_client.py

import time
import logging
import pika

class RabbitMQClient:
    def __init__(self, host, port, username, password, queue_name, reconnect_interval=30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.queue_name = queue_name
        self.reconnect_interval = reconnect_interval
        self.connection = None
        self.channel = None
        self.connected = False
        self.logger = logging.getLogger(__name__)

    def connect(self):
        while not self.connected:
            try:
                credentials = pika.PlainCredentials(self.username, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                self.connected = True
                self.logger.info(f"Connected to RabbitMQ on {self.host}:{self.port}")
            except pika.exceptions.AMQPConnectionError as e:
                self.logger.error(f"Connection failed: {e}. Retrying in {self.reconnect_interval} seconds.")
                time.sleep(self.reconnect_interval)

    def consume_messages(self, callback):
        if not self.connected:
            self.connect()

        def on_message(channel, method, properties, body):
            callback(body)
            channel.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=on_message)

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.stop_consuming()
        except Exception as e:
            self.logger.error(f"Error during consuming messages: {e}")
            self.connected = False
            self.connect()
            self.consume_messages(callback)

    def stop_consuming(self):
        if self.channel:
            self.channel.stop_consuming()
        if self.connection:
            self.connection.close()
        self.connected = False