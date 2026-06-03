
import os
from inkbytes.common.system.logger.log_formatters import CEFLogFormatter, ELFLogFormatter, W3CLogFormatter
import logging
from logging.handlers import SocketHandler, TimedRotatingFileHandler


# Custom handler for sending logs to a collector (e.g., a log aggregation service)
class CollectorHandler(logging.Handler):
    def __init__(self, collector_url):
        super().__init__()
        self.collector_url = collector_url
        # Initialize connection to the collector here
        # This could be an HTTP endpoint, a database, or another service

    def emit(self, record):
        try:
            log_entry = self.format(record)
            # Send log_entry to the collector
            # This is a placeholder; actual implementation depends on the collector's API
            # Example: requests.post(self.collector_url, data={'log': log_entry})
        except Exception:
            self.handleError(record)


# Module initialization function
def setup_logging(log_to='file', log_file_path='app.log', collector_url=None, socket_host=None, socket_port=None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to the lowest level to capture all logs

    if log_to == 'file':
        # Configure file handler
        file_handler = TimedRotatingFileHandler(log_file_path, when='midnight')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    elif log_to == 'socket' and socket_host and socket_port:
        # Configure socket handler
        socket_handler = SocketHandler(socket_host, socket_port)
        socket_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(socket_handler)
    elif log_to == 'collector' and collector_url:
        # Configure custom collector handler
        collector_handler = CollectorHandler(collector_url)
        collector_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(collector_handler)
    else:
        raise ValueError("Invalid logging configuration")

    return logger


# Example usage
if __name__ == '__main__':
    # Setup logging to a file
    setup_logging(log_to='file', log_file_path='/path/to/your/logfile.log')

    # Setup logging to a socket
    # setup_logging(log_to='socket', socket_host='localhost', socket_port=9999)

    # Setup logging to a collector
    # setup_logging(log_to='collector', collector_url='http://your.collector.url')

    logging.info("This is a test log message.")


def get_formatter(format_style, owner, **kwargs):
    if format_style == 'CEF':
        return CEFLogFormatter(**kwargs)
    elif format_style == 'ELF':
        return ELFLogFormatter(**kwargs)
    elif format_style == 'W3C':
        return W3CLogFormatter(**kwargs)
    # Fallback to standard formats
    elif format_style == 'simple':
        return logging.Formatter(f'{owner} - %(name)s - %(levelname)s - %(message)s')
    elif format_style == 'detailed':
        return logging.Formatter(f'{owner} - %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
    else:
        return logging.Formatter(f'{owner} - %(message)s')


class LogFormatterHandlerUtility:
    def __init__(self, log_file_path='/logs/messor'):
        self.log_file_path = log_file_path
        # Ensure the directory for the log file exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def setup_logger(self, name, owner='application', format_style='detailed', level=None):
        """Configures and returns a logger with specified format style, handlers, and owner."""
        logger = logging.getLogger(name)
        if level is not None:
            logger.setLevel(level)
        logger.addHandler(self.get_console_handler(format_style, owner))
        logger.addHandler(self.get_file_handler(format_style, owner))
        logger.propagate = False
        return logger

    def get_console_handler(self, format_style, owner):
        """Creates a console handler with specified format style and owner."""
        ch = logging.StreamHandler()
        ch.setFormatter(get_formatter(format_style, owner))
        return ch

    def get_file_handler(self, format_style, owner):
        """Creates a file handler with specified format style and owner."""
        fh = logging.FileHandler(self.log_file_path)
        fh.setFormatter(get_formatter(format_style, owner))
        return fh

    def get_formatter(self, format_style, owner):
        """Returns a logging formatter based on the specified style and owner."""
        if format_style == 'simple':
            formatter = logging.Formatter(f'{owner} - %(name)s - %(levelname)s - %(message)s')
        elif format_style == 'detailed':
            formatter = logging.Formatter(f'{owner} - %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                          datefmt='%Y-%m-%d %H:%M:%S')
        else:
            formatter = logging.Formatter(f'{owner} - %(message)s')
        return formatter


class LoggingUtility:
    FALLBACK_LOGGING_LEVEL = logging.INFO

    def __init__(self, log_file_path='', format_style='detailed', owner='application'):
        self.log_file_path = log_file_path
        self.format_style = format_style
        self.owner = owner
        self.configure_logging()

    def configure_logging(self):
        # Logic to set logging configuration based on environment, config files, or defaults
        logging_level = self.determine_logging_level()
        logging.basicConfig(level=logging_level)
        self.configure_root_logger(logging_level)

    def determine_logging_level(self):
        try:
            # Attempt to retrieve logging level from a configuration source
            return ...
        except Exception:
            return self.FALLBACK_LOGGING_LEVEL

    def get_formatter(self, format_style, **kwargs):
        # Factory method as described above
        ...

    def setup_logger(self, name, level=None, **kwargs):
        logger = logging.getLogger(name)
        if level:
            logger.setLevel(level)
        # Add handlers with formatters based on self.format_style
        ...
        return logger

    def configure_root_logger(self, level):
        # Configure the root logger using the utility's formatter and settings
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        # Add handlers and formatters as needed
        ...


class LoggerFactory(LogFormatterHandlerUtility):
    FALLBACK_LOGGING_LEVEL = logging.INFO

    @staticmethod
    def setup_logging(log_file_path='', format_style='detailed', owner='application'):
        try:
            import sysdictionary
            selected_logging_level = sysdictionary.LOGGING_CONF.get("LOG_LEVEL", LoggerFactory.FALLBACK_LOGGING_LEVEL)
            logging.basicConfig(level=selected_logging_level)
        except (ModuleNotFoundError, KeyError) as e:
            logging.basicConfig(level=LoggerFactory.FALLBACK_LOGGING_LEVEL)
            logging.warning(f"Failure to set logging configuration: {str(e)}")
        # Configure the root logger with the utility's formatting capabilities
        log_utility = LogFormatterHandlerUtility(log_file_path)
        log_utility.configure_root_logger(LoggerFactory.FALLBACK_LOGGING_LEVEL, format_style, owner)

    def create_logger(self, name, owner='application', format_style='detailed', level=None):
        return super().setup_logger(name, owner, format_style, level)

    @staticmethod
    def set_logger_level(level):
        logging.getLogger().setLevel(level)

    def configure_root_logger(self, level=logging.INFO, format_style='detailed', owner='root'):
        """Overrides the method to configure the root logger with a specified level and format."""
        super().setup_logger('', owner, format_style, level)
