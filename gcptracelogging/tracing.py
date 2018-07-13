import time
from threading import Thread, local

import b3
from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value
from gcptracelogging import global_vars

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128
trace_client = TraceServiceClient()
g = local()
b3.trace_len = 32


def start_span(incoming_headers, service_name, request_path, hostname):
    g.start_timestamp = _get_timestamp()
    g.span_display_name = f'{service_name}:{request_path} [{hostname}]'
    g.child_span_count = 0
    return b3.start_span(incoming_headers)


def end_span():
    b3_values = b3.values()
    timestamp = _get_timestamp()
    span_info = {
        'name': trace_client.span_path(global_vars.gcp_project_name, b3_values[b3.b3_trace_id], b3_values[b3.b3_span_id]),
        'span_id': b3_values[b3.b3_span_id],
        'display_name': _truncate_str(g.span_display_name, limit=SPAN_DISPLAY_NAME_BYTE_LIMIT),
        'start_time': g.start_timestamp,
        'end_time': timestamp,
        'parent_span_id': b3_values[b3.b3_parent_span_id],
        'same_process_as_parent_span': BoolValue(value=False),
        'child_span_count': Int32Value(value=g.child_span_count)
    }
    send_thread = Thread(target=_send_span, args=(span_info,))
    send_thread.start()
    b3.end_span()


class TracedSubSpan(b3.SubSpan):
    def __enter__(self):
        g.child_span_count += 1
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)


def _send_span(span_info):
    trace_client.create_span(**span_info)


def _get_timestamp():
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10 ** 9)
    timestamp = Timestamp(seconds=seconds, nanos=nanos)
    return timestamp


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
