import json
import logging
import threading

import pika
from collections import deque

from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from pika.credentials import PlainCredentials

logger = logging.getLogger(__name__)


class ThreadSafeRabbitClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: dict):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize(config)
        return cls._instance

    def _initialize(self, config: dict):
        credentials = PlainCredentials(
            config['rabbitmq']['username'], config['rabbitmq']['password']
        )
        self.connection = BlockingConnection(
            ConnectionParameters(
                host=config['rabbitmq']['host'],
                port=config['rabbitmq']['port'],
                credentials=credentials,
                heartbeat=config['rabbitmq']['heartbeat']
            )
        )
        self.channel = self.connection.channel()
        # Uncomment to declare the exchange
        # self.channel.exchange_declare(
        #     exchange=config['rabbitmq']['exchange'],
        #     exchange_type='topic',
        #     durable=True
        # )

    def publish(self, exchange: str, routing_key: str, message: str):
        with self._lock:  # Ensure thread safety during publishing
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message)
            )

    def close(self):
        with self._lock:
            if self.connection and self.connection.is_open:
                self.connection.close()
class RabbitMQHandler:
    def __init__(self, host="", port=5672, exchange_name="", queue_name="", local_queue_filename="", user_name="",
                 password="", routing_key="logs"):
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.local_queue_filename = local_queue_filename
        self.local_message_queue = self.load_local_queue_from_disk()
        self.connection = None
        self.channel = None
        self.connected = False
        self.try_connect()

    def try_connect(self):
        try:
            credentials = pika.PlainCredentials(self.user_name, self.password)
            parameters = pika.ConnectionParameters(host=self.host, port=self.port, credentials=credentials)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.setup_messaging()
            self.connected = True
            logger.info("Successfully connected to RabbitMQ.")
            self.flush_local_queue()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}. Messages will be queued locally.")
            self.connected = False


    def setup_messaging(self):
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type='fanout', durable=True)
        self.channel.queue_declare(queue=self.queue_name, durable=True)
        self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name)

    def load_local_queue_from_disk(self):
        try:
            with open(self.local_queue_filename, 'r') as f:
                return deque(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Local message queue file not found or is corrupted. Starting with an empty queue.")
            return deque()

    def save_local_queue_to_disk(self):
        with open(self.local_queue_filename, 'w') as f:
            json.dump(list(self.local_message_queue), f)

    def publish_message(self, message, routing_key=None, queue_name=None):
        routing_key = routing_key if routing_key else self.routing_key
        if self.connected:
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2))
            logger.info("Message published to RabbitMQ.")
            self.flush_local_queue()
        else:
            logger.warning("Not connected to RabbitMQ. Queueing message locally.")
            self.local_message_queue.append((self.exchange_name, routing_key, message, queue_name))
            self.save_local_queue_to_disk()

    def flush_local_queue(self):
        while self.local_message_queue and self.connected:
            exchange, routing_key, message, _ = self.local_message_queue.popleft()
            self.publish_message(message, routing_key)
        self.save_local_queue_to_disk()

    def close_connection(self):
        if self.connected and self.connection:
            self.connection.close()
            logger.info("RabbitMQ connection closed.")
