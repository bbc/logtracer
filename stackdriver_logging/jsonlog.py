import logging
import sys
import traceback
from datetime import datetime

from pythonjsonlogger import jsonlogger

from stackdriver_logging import b3, global_vars

LOG_SEVERITIES = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'WARN': 'WARNING',
    'ERROR': 'ERROR',
    'EXCEPTION': 'ERROR'
}


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """
        Add GCP StackDriver fields (https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry) to JSON logger
        output and remove default unused fields.
        """

        if record.exc_info:
            exception_class, exception, tb = record.exc_info
            tb_str = "\n".join(traceback.format_tb(tb))
            record.message = f"""Exception: {exception_class.__name__}({str(exception)})\nTraceback:\n{tb_str}"""

        b3_values = b3.values()
        if b3_values[b3.B3_TRACE_ID]:
            trace_name = f'projects/{global_vars.gcp_project_name}/traces/{b3_values[b3.B3_TRACE_ID]}'
        else:
            trace_name = None
        gcp_log_record = {
            'severity': LOG_SEVERITIES[record.levelname],
            'time': datetime.fromtimestamp(record.created),
            'logging.googleapis.com/trace': trace_name,
            'logging.googleapis.com/spanId': b3_values[b3.B3_SPAN_ID],
            'logging.googleapis.com/sourceLocation': {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            },
            'message': f'{record.name} - {record.message}'
        }

        log_record.update(gcp_log_record)
        log_record.pop('exc_info', None)


def configure_json_logging(project_name, service_name):
    """ Create a log record handler with a custom JSON formatter, then add it to the root logger."""
    global_vars.gcp_project_name = project_name
    global_vars.service_name = service_name
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)


def get_logger():
    return logging.getLogger(global_vars.service_name)
