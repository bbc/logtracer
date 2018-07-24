import time
from threading import Thread, local

from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value

from stackdriver_logging import b3
from stackdriver_logging import global_vars
from stackdriver_logging.b3 import generate_subspan_values

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128
trace_client = TraceServiceClient()
thread_memory = local()
thread_memory.span_started = False
b3.TRACE_LEN = 32


class TraceException(Exception):
    pass


def start_traced_span(incoming_headers, request_path):
    thread_memory.start_timestamp = _get_timestamp()
    thread_memory.span_display_name = f'{global_vars.service_name}:{request_path}'
    thread_memory.child_span_count = 0
    thread_memory.span_started = True
    return b3.start_span(incoming_headers)


def end_traced_span():
    b3_values = b3.values()
    timestamp = _get_timestamp()
    span_info = {
        'name': trace_client.span_path(global_vars.gcp_project_name, b3_values[b3.B3_TRACE_ID],
                                       b3_values[b3.B3_SPAN_ID]),
        'span_id': b3_values[b3.B3_SPAN_ID],
        'display_name': _truncate_str(thread_memory.span_display_name, limit=SPAN_DISPLAY_NAME_BYTE_LIMIT),
        'start_time': thread_memory.start_timestamp,
        'end_time': timestamp,
        'parent_span_id': b3_values[b3.B3_PARENT_SPAN_ID],
        'same_process_as_parent_span': BoolValue(value=False),
        'child_span_count': Int32Value(value=thread_memory.child_span_count)
    }
    post_to_api_job = Thread(target=_post_span, args=(span_info,))
    post_to_api_job.start()
    b3.end_span()
    thread_memory.span_open = False


def generate_traced_subspan_values():
    if not thread_memory.span_started:
        raise TraceException('Span must be started using `start_span` before creating a subspan.')
    thread_memory.child_span_count += 1
    return generate_subspan_values()


def _post_span(span_info):
    """Post span to Trace API."""
    trace_client.create_span(**span_info)


def _get_timestamp():
    now = time.time()
    seconds, nanos = _to_seconds_and_nanos(now)
    timestamp = Timestamp(seconds=seconds, nanos=nanos)
    return timestamp


def _to_seconds_and_nanos(fractional_seconds):
    seconds = int(fractional_seconds)
    nanos = int((fractional_seconds - seconds) * 10 ** 9)
    return seconds, nanos


def _truncate_str(str_to_truncate, limit):
    """
    Truncate a string if exceed limit and record the truncated bytes count.
    """
    str_bytes = str_to_truncate.encode('utf-8')
    trunc = {
        'value': str_bytes[:limit].decode('utf-8', errors='ignore'),
        'truncated_byte_count': len(str_bytes) - len(str_bytes[:limit]),
    }
    return trunc
