import logging
import os
from logging.handlers import TimedRotatingFileHandler

from inkbytes.common.system.logger.rabbit_log_handler import RabbitMQLoggingHandler


class LoggerConfig:
    def __init__(self):
        self.log_file = ''
        self.log_level = logging.INFO
        self.handler_type = 'file'
        self.log_formatter: logging.Formatter = None
        self.extra_config = {}
        self.rotation_params = None  # New field for rotation parameters

    def setFormatter(self, formatter):
        self.log_formatter = formatter


class LoggerFactory:

    @staticmethod
    def create_logger(module_name: str, logger_config: [LoggerConfig]):
        logger_info = logging.getLogger(module_name)
        for config in logger_config:
            handler = LoggerFactory._create_handler(config)
            if handler:
                logger_info.addHandler(handler)

        return logger_info

    @staticmethod
    def _create_handler(config: LoggerConfig):
        if config.handler_type == 'file':
            return LoggerFactory._configure_file_handler(config)
        elif config.handler_type == 'timed_rotating_file':
            return LoggerFactory._configure_timed_rotating_file_handler(config)
        elif config.handler_type == 'rabbitmq':
            return LoggerFactory._configure_rabbitmq_handler(config)
        else:
            return None

    @staticmethod
    def _configure_file_handler(config: LoggerConfig):
        # Ensure directory exists
        os.makedirs(os.path.dirname(config.log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(config.log_formatter)
        file_handler.setLevel(config.log_level)

        return file_handler
        
    @staticmethod
    def _configure_timed_rotating_file_handler(config: LoggerConfig):
        # Ensure directory exists
        os.makedirs(os.path.dirname(config.log_file), exist_ok=True)
        
        # Set default rotation parameters if none provided
        rotation_params = config.rotation_params or {
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'encoding': 'utf-8',
            'delay': False,
            'utc': False
        }
        
        # Create handler
        handler = TimedRotatingFileHandler(
            filename=config.log_file,
            when=rotation_params.get('when', 'midnight'),
            interval=rotation_params.get('interval', 1),
            backupCount=rotation_params.get('backupCount', 30),
            encoding=rotation_params.get('encoding', 'utf-8'),
            delay=rotation_params.get('delay', False),
            utc=rotation_params.get('utc', False)
        )
        
        # Set suffix format for rotated files if provided
        if 'suffix' in rotation_params:
            handler.suffix = rotation_params['suffix']
        
        handler.setFormatter(config.log_formatter)
        handler.setLevel(config.log_level)
        
        return handler

    @staticmethod
    def _configure_rabbitmq_handler(config: LoggerConfig):
        rabbit_logger_handler = RabbitMQLoggingHandler(config.extra_config)
        rabbit_logger_handler.setFormatter(config.log_formatter)
        rabbit_logger_handler.setLevel(config.log_level)
        return rabbit_logger_handler