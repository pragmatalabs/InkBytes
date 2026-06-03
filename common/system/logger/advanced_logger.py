import functools
import logging
from enum import Enum
from typing import Callable
from inkbytes.common.api.ampq_mq import ThreadSafeRabbitClient
from inkbytes.common.system.logger.log_formatters import EnhancedSyslogFormatter


class LogDestination(Enum):
    FILE = "file"
    RABBIT = "rabbit"
    CONSOLE = "console"

class AdvancedLogger:
    def __init__(self, config: dict):
        self.logger = None
        self.config = config
        self.rabbit_client = None
        self.rabbit_formatter = None
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=self.config['log_level'])
        self.logger = logging.getLogger(self.config['logger_name'])

        # File log setup
        if LogDestination.FILE.value in self.config['destinations']:
            file_handler = logging.FileHandler(self.config['log_file'])
            file_formatter = logging.Formatter(self.config['log_format'])
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # RabbitMQ log setup
            # RabbitMQ log setup
        if LogDestination.RABBIT.value in self.config['destinations']:
                self.rabbit_client = ThreadSafeRabbitClient(self.config)
                self.rabbit_formatter = EnhancedSyslogFormatter(
                    fmt=self.config['log_format'],
                    app_name=self.config['logger_name']
                )

    def log_to_rabbitmq(self, level: int, message: str):
        if self.rabbit_client:
            # Format the message for RabbitMQ
            record = logging.LogRecord(
                name=self.logger.name,
                level=level,
                pathname=__file__,
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            formatted_message = self.rabbit_formatter.format(record)
            self.rabbit_client.publish(
                exchange=self.config['rabbitmq']['exchange'],
                routing_key=self.config['rabbitmq']['routing_key'],
                message=formatted_message
            )


    def log(self, level: int, message: str):
        # Log to standard logger
        self.logger.log(level, message)
        # Also log to RabbitMQ if configured
        if LogDestination.RABBIT.value in self.config['destinations']:
            self.log_to_rabbitmq(level, message)

    def log_function(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_details = {
                'custom_funcName': func.__name__,
                'custom_module': func.__module__,
                'custom_args': args if args else '-',
            }
            self.log(logging.INFO, f"{func.__name__} {args} {kwargs} {func_details}")
            try:
                result = func(*args, **kwargs)
                self.log(logging.INFO, f"Results:{func.__name__} result: {result} {func_details}")
                return result
            except Exception as e:
                self.log(logging.ERROR, f"Exception in {func.__name__}: {str(e)}")
                raise

        return wrapper

    def __del__(self):
        if self.rabbit_client:
            self.rabbit_client.close()