import logging


class LoggerFactory():
    FALLBACK_LOGGING_LEVEL = logging.WARNING

    @staticmethod
    def setup_logging():
        try:

            selected_logging_level = sysdictionary.LOGGING_CONF.get("LOG_LEVEL", LoggerFactory.FALLBACK_LOGGING_LEVEL)
            logging.basicConfig(level=selected_logging_level)
        except (ModuleNotFoundError, KeyError) as e:
            logging.basicConfig(level=LoggerFactory.FALLBACK_LOGGING_LEVEL)
            logging.warning(f"Failure to set logging configuration: {str(e)}")

    @staticmethod
    def create_logger(name):
        return logging.getLogger(name)

    @staticmethod
    def set_logger_level(level):
        logging.getLogger().setLevel(level)

# Usage:
# LoggerFactory.setup_logging()
