import time
from threading import Thread, local

from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value

from stackdriver_logging import _b3
from stackdriver_logging import _global_vars
from stackdriver_logging._b3 import generate_new_subspan_values

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128
trace_client = TraceServiceClient()
thread_memory = local()
thread_memory.span_started = False
_b3.TRACE_LEN = 32


class TraceException(Exception):
    pass


def configure_tracing(post_spans_to_api=False):
    _global_vars.post_spans_to_api = post_spans_to_api


def start_traced_span(incoming_headers, request_path):
    """
    Start a b3 span and keep track of extra details for tracing.

    Arguments:
        incoming_headers: Incoming request headers. These could be http, or part of a GRPC message.
        request_path (str): Path of the endpoint of the incoming request.
    """
    thread_memory.span = {
        "start_timestamp": _get_timestamp(),
        "display_name": f'{_global_vars.service_name}:{request_path}',
        "child_span_count": 0,
    }
    _b3.start_span(incoming_headers)


def end_traced_span():
    """
    End a b3 span and collect details about the span, then post it to the API
    (depending on the `_global_vars.post_spans_to_api` flag).
    """
    b3_values = _b3.values()
    end_timestamp = _get_timestamp()
    span_info = {
        'name': trace_client.span_path(_global_vars.gcp_project_name, b3_values[_b3.B3_TRACE_ID],
                                       b3_values[_b3.B3_SPAN_ID]),
        'span_id': b3_values[_b3.B3_SPAN_ID],
        'display_name': _truncate_str(thread_memory.span['display_name'], limit=SPAN_DISPLAY_NAME_BYTE_LIMIT),
        'start_time': thread_memory.span['start_timestamp'],
        'end_time': end_timestamp,
        'parent_span_id': b3_values[_b3.B3_PARENT_SPAN_ID],
        'same_process_as_parent_span': BoolValue(value=False),
        'child_span_count': Int32Value(value=thread_memory.span['child_span_count'])
    }
    if _global_vars.post_spans_to_api:
        post_to_api_job = Thread(target=_post_span, args=(span_info,))
        post_to_api_job.start()
    _b3.end_span()
    del thread_memory.span


def generate_traced_subspan_values():
    """
    For use in a one-off downstream call. Use this to generate the values to pass to a downstream service.
    """
    if not hasattr(thread_memory,'span'):
        raise TraceException('Span must be started using `start_span` before creating a subspan.')
    thread_memory.span["child_span_count"] += 1
    return generate_new_subspan_values()


def _post_span(span_info):
    """Post span to Trace API."""
    trace_client.create_span(**span_info)


def _get_timestamp():
    """Get timestamp in a format Stackdriver Trace accepts it."""
    now = time.time()
    seconds, nanos = _to_seconds_and_nanos(now)
    timestamp = Timestamp(seconds=seconds, nanos=nanos)
    return timestamp


def _to_seconds_and_nanos(fractional_seconds):
    """Convert fractional seconds to seconds and nanoseconds."""
    seconds = int(fractional_seconds)
    nanos = int((fractional_seconds - seconds) * 10 ** 9)
    return seconds, nanos


def _truncate_str(str_to_truncate, limit):
    """Truncate a string if exceed limit and record the truncated bytes count."""
    str_bytes = str_to_truncate.encode('utf-8')
    trunc = {
        'value': str_bytes[:limit].decode('utf-8', errors='ignore'),
        'truncated_byte_count': len(str_bytes) - len(str_bytes[:limit]),
    }
    return trunc
