import logging
from inkbytes.common.api.ampq_mq import RabbitMQHandler


class RabbitMQLoggingHandler(logging.Handler):
    def __init__(self, config):
        super().__init__()
        self.host = config.get('host')
        self.routing_key = config.get('routing_key')
        self.local_queue_filename = config.get('local_queue_filename')
        self.queue_name = config.get('queue_name')
        self.exchange_name = config.get('exchange_name')
        self.port = config.get('port')
        self.user_name = config.get('user_name')
        self.password = config.get('password')
        # Initialize RabbitMQHandler with provided parameters.
        self.rabbitmq = RabbitMQHandler(host=self.host, port=self.port, exchange_name=self.exchange_name,
                                        queue_name=self.queue_name,
                                        user_name=self.user_name, password=self.password,
                                        local_queue_filename=self.local_queue_filename)

    def emit(self, record):
        """
        Emit a log record.

        Attempts to publish the log record to the configured RabbitMQ exchange. If the RabbitMQ connection is not
        open, it tries to reconnect.
        """
        if not self.rabbitmq.channel.is_open:
            self.rabbitmq.try_connect()

        message = self.format(record)
        try:
            # Directly use publish_message which handles connection checks internally
            self.rabbitmq.publish_message(message=message, routing_key=self.routing_key)
        except Exception as e:  # Catch broader exceptions as RabbitMQ publishing could fail for many reasons
            # Fallback logging in case RabbitMQ publishing fails.
            # Use a root logger to avoid recursive logging issues in case the fallback itself fails.
            logging.getLogger().error(f"Failed to publish message to RabbitMQ: {e}", exc_info=True)
