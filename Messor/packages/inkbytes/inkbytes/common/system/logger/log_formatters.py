import json
import logging
import uuid


class CEFLogFormatter(logging.Formatter):
    """
    A custom log formatter for CEF (Common Event Format).
    Formats log records to CEF standard, allowing integration with security information and event management (SIEM) systems.

    Attributes:
        vendor (str): Vendor name.
        product (str): Product name.
        version (str): Version of the product.
        signature (str): Identifier for the type of event being logged.
        name (str): Descriptive name of the event.
        severity (str): Severity level of the event.
    """

    def __init__(self, vendor, product, version, signature, name, severity):
        """
        Initializes the formatter with basic CEF configuration.
        """
        super().__init__()
        self.vendor = vendor
        self.product = product
        self.version = version
        self.signature = signature
        self.name = name
        self.severity = severity

    def format(self, record):
        """
        Formats a log record into a CEF compliant string.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: A CEF formatted string representing the log record.
        """
        cef_header = f"CEF:0|{self.vendor}|{self.product}|{self.version}|{self.signature}|{self.name}|{self.severity}"
        extension = f"cs1Label=LoggerName cs1={record.name} cs2Label=LogLevel cs2={record.levelname} msg={record.getMessage()}"
        return f"{cef_header}|{extension}"


class ELFLogFormatter(logging.Formatter):
    """
    A custom log formatter for the Extended Log File (ELF) format.
    It is designed to format log records into a configurable ELF string format,
    commonly used for web server logs and other internet services.

    This formatter allows for the inclusion of various standard log attributes such as remote host,
    request line, status, and response size, among others, in the formatted log message.

    The format and date format can be customized during initialization.

    Parameters:
    - fmt (str, optional): The log format string. If None, a default ELF format is used.
    - datefmt (str, optional): The format string for date/time representation.
    """

    def __init__(self, fmt=None, datefmt=None):
        """
        Initializes the formatter with the given format and date format strings.
        """
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):
        """
        Formats a log record into an ELF string based on the formatter's configuration.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: A string formatted in the Extended Log File format.
        """
        # Extracting attributes with defaults for missing values
        remote_host = getattr(record, 'remote_host', '-')
        request = getattr(record, 'request', '-')
        status = getattr(record, 'status', '-')
        response_size = getattr(record, 'response_size', '-')
        time_received = self.formatTime(record, self.datefmt)

        # Constructing the ELF format string
        elf_string = f'{remote_host} - - [{time_received}] "{request}" {status} {response_size}'
        return elf_string


class W3CLogFormatter(logging.Formatter):
    """
    Custom log formatter for formatting logs in the W3C Extended Log File Format.

    This formatter allows for flexible configuration of log fields, enabling it to be tailored to specific logging requirements.

    Parameters:
    - fmt (str, optional): The log format string. Not used in this formatter as the format is determined by the configured fields.
    - datefmt (str, optional): The format string for date/time representation. Defaults to '%Y-%m-%d %H:%M:%S'.
    - fields (list, optional): A list of fields to include in the log message. Defaults to a basic set of W3C fields.
    """

    default_fields = ['date', 'time', 'c-ip', 'cs-method', 'cs-uri-stem', 'cs-uri-query', 'sc-status', 'sc-bytes']

    def __init__(self, fmt=None, datefmt='%Y-%m-%d %H:%M:%S', fields=None):
        """
        Initializes the formatter with the given date format and fields.
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.fields = fields if fields is not None else self.default_fields

    def format(self, record):
        """
        Formats a log record into a W3C Extended Log File Format string based on the configured fields.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: A string formatted according to the W3C Extended Log File Format.
        """
        log_entry = {
            'date': self.formatTime(record, "%Y-%m-%d"),
            'time': self.formatTime(record, "%H:%M:%S"),
            'c-ip': getattr(record, 'client_ip', '-'),
            'cs-method': getattr(record, 'method', '-'),
            'cs-uri-stem': getattr(record, 'uri_stem', '-'),
            'cs-uri-query': getattr(record, 'query', '-'),
            'sc-status': getattr(record, 'status', '-'),
            'sc-bytes': getattr(record, 'bytes_sent', '-')
        }

        formatted_log = ' '.join([f'{field}={log_entry[field]}' for field in self.fields if field in log_entry])
        return formatted_log


class SyslogFormatter(logging.Formatter):
    """
    Custom log formatter for formatting logs in a Syslog-compatible format.

    This formatter formats log records with essential Syslog information, including
    a timestamp, an application name, and the log message. It's designed to be flexible,
    allowing customization of the format if needed.

    Parameters:
    - fmt (str, optional): The log format string, defining how the log message is structured.
    - datefmt (str, optional): The format string for date/time representation. Defaults to RFC 3339 format.
    - app_name (str, optional): The name of the application or process generating the log message.
    """

    def __init__(self, fmt=None, datefmt='%Y-%m-%dT%H:%M:%S', app_name='Application'):
        """
        Initializes the formatter with the given format, date format, and application name.
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.app_name = app_name

    def format(self, record):
        """
        Formats a log record into a Syslog-compatible string based on the configured format.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: A string formatted according to Syslog standards, including a timestamp,
                 application name, and the log message.
        """
        # Ensuring the record is aware of the application name
        record.app_name = self.app_name
        # Preparing the message with a standard Syslog header (timestamp and app_name)
        syslog_header = f"{self.formatTime(record, self.datefmt)} {self.app_name}:"
        # Formatting the message according to the user-defined or default format
        formatted_message = super().format(record)
        return f"{syslog_header} {formatted_message}"


import logging


class NormalEnhancedSyslogFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt='%Y-%m-%dT%H:%M:%S', app_name='Application'):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.app_name = app_name

    def format(self, record):
        record.app_name = self.app_name
        level_name = record.levelname
        # Only prepend decorator context when the record actually carries it.
        # Plain logger.warning() calls have no custom_funcName, so omitting
        # the prefix stops the `unknown in unknown (args: -)` noise on every
        # regular log line (P5 fix, 2026-06-10).
        custom_func = getattr(record, 'custom_funcName', None)
        if custom_func:
            extra_details = (
                f"{custom_func} in "
                f"{getattr(record, 'custom_module', 'unknown')} "
                f"(args: {getattr(record, 'custom_args', '-')}) - "
            )
        else:
            extra_details = ""
        syslog_header = f"{self.formatTime(record, self.datefmt)} {self.app_name}:"
        formatted_message = super().format(record)
        return f"{syslog_header} [{level_name}] {extra_details}{formatted_message}"


class EnhancedSyslogFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt='%Y-%m-%dT%H:%M:%S', app_name='Application'):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.app_name = app_name

    def format(self, record):
        print(record)
        # Create a dictionary with all the log record information
        log_record = {

            "id": str(uuid.uuid4()),
            "timestamp": str(self.formatTime(record, self.datefmt)),
            "app_name": self.app_name,
            "level": record.levelname,
            "message": super().format(record),
            "funcName": str(getattr(record.funcName, 'custom_funcName', 'unknown')),
            "module": str(getattr(record.module, 'custom_module', 'unknown')),
            "args": str(getattr(record.exc_info, 'custom_args', '-')),
        }

        # Convert the dictionary to a JSON string
        #return json.dumps({"pattern": "logs", "data": log_record})
        return log_record


def log_function_activity(logger):
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_details = {
                'custom_funcName': func.__name__,  # Avoid conflicts with built-in attributes
                'custom_module': func.__module__,
                'custom_args': args if args else '-',
            }
            try:
                logger.info(f"Executing {func.__name__}", extra=func_details)
                result = func(*args, **kwargs)
                logger.info(f"Executed {func.__name__} with result: {result}", extra=func_details)
            except Exception as e:
                # Log exceptions as ERRORs
                logger.error(f"Error executing {func.__name__}: {e}", extra=func_details)
                raise  # Optionally re-raise the exception
            return result

        return wrapper

    return decorator
