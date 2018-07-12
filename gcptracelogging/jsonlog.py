import logging
import sys
import traceback
from datetime import datetime

from b3 import b3_span_id, values, b3_trace_id
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """
        Add GCP StackDriver fields (https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry) to JSON logger
        output and remove default unused fields.
        """
        log_severities = {
            'DEBUG': 'DEBUG',
            'INFO': 'INFO',
            'WARNING': 'WARNING',
            'WARN': 'WARNING',
            'ERROR': 'ERROR',
            'EXCEPTION': 'ERROR'
        }

        if record.exc_info:
            exception_class, exception, tb = record.exc_info
            tb_str = "\n".join(traceback.format_tb(tb))
            record.message = f"""Exception: {exception_class.__name__}({str(exception)})\nTraceback:\n{tb_str}"""

        b3_values = values()
        gcp_log_record = {
            'severity': log_severities[record.levelname],
            'time': datetime.fromtimestamp(record.created),
            'logging.googleapis.com/trace': f'projects/bbc-connected-data/traces/{b3_values[b3_trace_id]}',
            'logging.googleapis.com/spanId': b3_values[b3_span_id],
            'logging.googleapis.com/sourceLocation': {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            },
            'message': f'{record.name} - {record.message}'
        }

        log_record.update(gcp_log_record)
        log_record.pop('exc_info', None)


def configure_json_logging():
    """ Create a log record handler with a custom JSON formatter, then add it to the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
