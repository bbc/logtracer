import logging
import sys
import traceback
from datetime import datetime
from enum import Enum

from pythonjsonlogger import jsonlogger

from logtracer.exceptions import SpanNotStartedError
from logtracer.tracing.tracer import B3_SPAN_ID, B3_TRACE_ID

LOG_SEVERITIES = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'WARN': 'WARNING',
    'ERROR': 'ERROR',
    'EXCEPTION': 'ERROR'
}


class Formatters(Enum):
    local = 'local'
    stackdriver = 'stackdriver'


class JsonFormatter(jsonlogger.JsonFormatter):
    tracer = None

    def __init__(self, stackdriver, project_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer = None
        self.stackdriver = stackdriver
        self.project_name = project_name

    def add_fields(self, log_record, record, message_dict):
        """
        Add GCP StackDriver fields (https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry) to JSON logger
        output and remove default unused fields.
        """

        if record.exc_info:
            _format_message_for_exception(record)

        gcp_log_record = _generate_log_record(record, stackdriver=self.stackdriver)

        if self.tracer:
            _add_span_values(self.tracer, gcp_log_record, self.stackdriver, self.project_name)

        log_record.update(gcp_log_record)
        log_record.pop('exc_info', None)


def _generate_log_record(record, stackdriver=False):
    """
    Generate some details of the log record to write.

    Arguments:
        record (logging.LogRecord): default argument into the logging formatter
        stackdriver (bool): add google prefixes if true
    """
    prefix = 'logging.googleapis.com/' if stackdriver else ''

    message = record.message if record.message else str(record.msg)

    json_log_record = {
        'severity': LOG_SEVERITIES[record.levelname],
        'message': f'{record.name} - {message}',
        'time': datetime.fromtimestamp(record.created),
        f'{prefix}sourceLocation': {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }
    }

    return json_log_record


def _add_span_values(tracer, json_log_record, stackdriver, project_name):
    """Add span values to log entry if a tracer instance is present and the log entry is written within a span."""
    try:
        span_values = tracer.current_span['values']

        trace_name = span_values[B3_TRACE_ID] if not stackdriver \
            else f'projects/{project_name}/traces/{span_values[B3_TRACE_ID]}'

        prefix = 'logging.googleapis.com/' if stackdriver else ''

        json_log_record.update({
            f'{prefix}trace': trace_name,
            f'{prefix}spanId': span_values[B3_SPAN_ID]
        })

    except SpanNotStartedError:
        pass


def _format_message_for_exception(record):
    """
    Check if the log record contains exception information (from usage of logger.exception), if so then format the
    message with the stack trace.
    """
    exception_class, exception, tb = record.exc_info
    tb_str = "\n".join(traceback.format_tb(tb))
    record.message = f"""Exception: {exception_class.__name__}({str(exception)})\nTraceback:\n{tb_str}"""


class JSONLoggerFactory:

    def __init__(self, project_name, service_name, logging_format, logger_per_module=False):
        """
        Class to handle creation of a logger instance with a JSON formatter. Only initialise this ONCE and reuse it
        across your app.

        Arguments:
            project_name (str): name of your GCP project
            service_name (str): name of your app
            logging_format (Formatters): enum of platform for log formatting
            logger_per_module (bool): toggle namespacing loggers per module eg `snowdrop.services.bramble.client`
                vs `snowdrop`
        """
        self.project_name = project_name
        self.service_name = service_name
        self.logger_per_module = logger_per_module

        if not isinstance(logging_format, Formatters):
            raise ValueError('Logging format must be from Formatters enum')

        handler = logging.StreamHandler(sys.stdout)
        stackdriver = True if logging_format == Formatters.stackdriver else False
        handler.setFormatter(JsonFormatter(stackdriver, project_name))

        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

    def get_logger(self, module_name='', level='INFO'):
        """Use this function to get the logger throughout your app."""
        module_name = '' if not self.logger_per_module else module_name
        module_name = f".{module_name}" if module_name else module_name
        logger = logging.getLogger(f'{self.service_name}{module_name}')
        logger.setLevel(level)
        return logger
