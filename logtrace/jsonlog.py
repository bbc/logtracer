import logging
import sys
import traceback
from datetime import datetime

from pythonjsonlogger import jsonlogger

from logtrace import _b3, _global_vars

LOG_SEVERITIES = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'WARN': 'WARNING',
    'ERROR': 'ERROR',
    'EXCEPTION': 'ERROR'
}


class StackdriverJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """
        Add GCP StackDriver fields (https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry) to JSON logger
        output and remove default unused fields.
        """

        if record.exc_info:
            exception_class, exception, tb = record.exc_info
            tb_str = "\n".join(traceback.format_tb(tb))
            record.message = f"""Exception: {exception_class.__name__}({str(exception)})\nTraceback:\n{tb_str}"""

        gcp_log_record = {
            'severity': LOG_SEVERITIES[record.levelname],
            'time': datetime.fromtimestamp(record.created),
            'logging.googleapis.com/sourceLocation': {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            },
            'message': f'{record.name} - {record.message}'
        }

        b3_values = _b3.values()
        if b3_values[_b3.B3_TRACE_ID]:
            trace_name = f'projects/{_global_vars.gcp_project_name}/traces/{b3_values[_b3.B3_TRACE_ID]}'
            gcp_log_record.update({
                'logging.googleapis.com/trace': trace_name,
                'logging.googleapis.com/spanId': b3_values[_b3.B3_SPAN_ID],
            })

        log_record.update(gcp_log_record)
        log_record.pop('exc_info', None)


class LocalJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """
        Add GCP StackDriver fields (https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry) to JSON logger
        output and remove default unused fields.
        """
        if record.exc_info:
            exception_class, exception, tb = record.exc_info
            tb_str = "\n".join(traceback.format_tb(tb))
            record.message = f"""Exception: {exception_class.__name__}({str(exception)})\nTraceback:\n{tb_str}"""

        json_log_record = {
            'severity': LOG_SEVERITIES[record.levelname],
            'time': datetime.fromtimestamp(record.created),
            'sourceLocation': {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            },
            'message': f'{record.name} - {record.message}'
        }

        b3_values = _b3.values()
        if b3_values[_b3.B3_TRACE_ID]:
            json_log_record.update({
                'traceId': b3_values[_b3.B3_TRACE_ID],
                'spanID': b3_values[_b3.B3_SPAN_ID]
            })
        log_record.update(json_log_record)
        log_record.pop('exc_info', None)


LOGGING_FORMATS = {
    'stackdriver': StackdriverJsonFormatter,
    'local': LocalJsonFormatter
}


def configure_json_logging(project_name, service_name, logging_format):
    """
    Set globals and create a log record handler with a custom JSON formatter, then add it to the root logger.

    Arguments:
        project_name (str): name of your GCP project
        service_name (str): name of your app
        logging_format (str): name of platform (for log formatting)
    """
    _global_vars.gcp_project_name = project_name
    _global_vars.service_name = service_name

    handler = logging.StreamHandler(sys.stdout)
    formatter = LOGGING_FORMATS[logging_format]
    handler.setFormatter(formatter())

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)


def get_logger():
    """Use this function to get the logger throughout your app."""
    return logging.getLogger(_global_vars.service_name)
