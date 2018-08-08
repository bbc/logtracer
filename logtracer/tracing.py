import os
import time
from binascii import hexlify
from threading import Thread, local

from google.auth.exceptions import DefaultCredentialsError
from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value

from logtracer import _b3
from logtracer import _global_vars

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128


class TraceException(Exception):
    pass


class StackDriverAuthError(Exception):
    pass


class Tracer:
    def __init__(self, json_logger_handler, post_spans_to_stackdriver_api=False):
        self.project_name = json_logger_handler.project_name
        self.service_name = json_logger_handler.service_name
        self.post_spans_to_stackdriver_api = post_spans_to_stackdriver_api
        self.spans = {}
        self._logger = json_logger_handler.get_logger(__name__)
        if self.post_spans_to_stackdriver_api:
            try:
                self.trace_client = TraceServiceClient()
            except DefaultCredentialsError:
                raise StackDriverAuthError('Cannot post spans to API, no authentication credentials found.')

    def set_logging_level(self, level):
        self._logger.setLevel(level)

    def start_traced_span(self, incoming_headers, request_path):
        """
        Start a b3 span and keep track of extra details for tracing.

        Arguments:
            incoming_headers: Incoming request headers. These could be http, or part of a GRPC message.
            request_path (str): Path of the endpoint of the incoming request.
        """
        span_values = {
            B3_TRACE_ID: incoming_headers.get(B3_TRACE_ID) or _generate_identifier(TRACE_LEN),
            B3_PARENT_SPAN_ID: incoming_headers.get(B3_PARENT_SPAN_ID),
            B3_SPAN_ID: incoming_headers.get(B3_SPAN_ID) or _generate_identifier(SPAN_LEN),
            B3_SAMPLED: incoming_headers.get(B3_SAMPLED),
            B3_FLAGS: incoming_headers.get(B3_FLAGS)
        }

        self.spans[span_values[B3_SPAN_ID]] = {
            "start_timestamp": _get_timestamp(),
            "display_name": f'{_global_vars.service_name}:{request_path}',
            "child_span_count": 0,
            "values": span_values
        }

    def end_traced_span(self, post_span=True):
        """
        End a b3 span and collect details about the span, then post it to the API
        (depending on the `_global_vars.post_spans_to_api` flag).
        """
        b3_values = values()
        end_timestamp = _get_timestamp()
        if self.post_spans_to_stackdriver_api:
            name = self.trace_client.span_path(_global_vars.gcp_project_name, b3_values[B3_TRACE_ID],
                                               b3_values[B3_SPAN_ID])
        else:
            name = f'{_global_vars.gcp_project_name}/{b3_values[_b3.B3_TRACE_ID]}/{b3_values[_b3.B3_SPAN_ID]}'

        span_info = {
            'name': name,
            'span_id': b3_values[B3_SPAN_ID],
            'display_name': _truncate_str(self.span['display_name'], limit=SPAN_DISPLAY_NAME_BYTE_LIMIT),
            'start_time': self.span['start_timestamp'],
            'end_time': end_timestamp,
            'parent_span_id': b3_values[B3_PARENT_SPAN_ID],
            'same_process_as_parent_span': BoolValue(value=False),
            'child_span_count': Int32Value(value=self.span['child_span_count'])
        }
        if self.post_spans_to_stackdriver_api and post_span:
            post_to_api_job = Thread(target=_post_span, args=(self.trace_client, span_info))
            post_to_api_job.start()
        end_span()
        self.span = None

    def generate_new_traced_subspan_values(self):
        """
        For use in a one-off downstream call. Use this to generate the values to pass to a downstream service.
        """
        if not self.span:
            raise TraceException('Span must be started using `start_span` before creating a subspan.')
        self.span["child_span_count"] += 1
        return generate_new_subspan_values()

    @property
    def memory(self):
        # todo:
        #   implement non thread safe memory here as class
        #   encourage overriding in helpers, for flask use g for grpc use ???
        #   finish merging b3 values stuff into here
        #
        pass



def _post_span(trace_client, span_info):
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


TRACE_LEN = 32
SPAN_LEN = 16
B3_TRACE_ID = 'X-B3-TraceId'
B3_PARENT_SPAN_ID = 'X-B3-ParentSpanId'
B3_SPAN_ID = 'X-B3-SpanId'
B3_SAMPLED = 'X-B3-Sampled'
B3_FLAGS = 'X-B3-Flags'
B3_HEADERS = [B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID, B3_SAMPLED, B3_FLAGS]
b3 = local()


class SpanError(Exception):
    pass


def values():
    """
    Get the full current set of B3 values. If a span is not started then return null values by default.

    Returns:
        (dict): Contains the keys "X-B3-TraceId", "X-B3-ParentSpanId", "X-B3-SpanId", "X-B3-Sampled" and
                "X-B3-Flags" for the current span or subspan. NB some of the values are likely be None, but
                all keys will be present.
    """
    default = {
        B3_TRACE_ID: None,
        B3_PARENT_SPAN_ID: None,
        B3_SPAN_ID: None,
        B3_SAMPLED: None,
        B3_FLAGS: None
    }
    return default if not hasattr(b3, 'span') else b3.span


def end_span():
    """Closes the span by deleting the span values from the thread memory."""
    if not hasattr(b3, "span"):
        raise SpanError('`end_span` must be called after `start_span`')
    del b3.span


def generate_new_subspan_values():
    """
    Sets up new span values to contact a downstream service.
    This is used when making a downstream service call. It returns a dict containing the required sub-span headers.
    Each downstream call you make is handled as a new span, so call this every time you need to contact another service.
    Entries with the value `None` are filtered out.

    For the specification, see: https://github.com/openzipkin/b3-propagation

    Returns:
         (dict): contains header values for a downstream request. This can be passed directly to e.g. requests.get(...).
    """
    if not hasattr(b3, 'span'):
        raise SpanError('`generate_new_subspan_values` must be called after `start_span`')

    parent_values = values()
    subspan_values = {
        B3_TRACE_ID: parent_values[B3_TRACE_ID],
        B3_PARENT_SPAN_ID: parent_values[B3_SPAN_ID],
        B3_SPAN_ID: _generate_identifier(SPAN_LEN),
        B3_SAMPLED: parent_values[B3_SAMPLED],
        B3_FLAGS: parent_values[B3_FLAGS]
    }
    subspan_values = {k: v for k, v in subspan_values.items() if v}
    return subspan_values


def _generate_identifier(identifier_length):
    """
    Generates a new, random identifier in B3 format.
    Arguments:
        identifier_length (int): length of identifier to generate
    Returns:
        (str): A 64-bit random identifier, rendered as a hex String.
    """
    if not _is_power2(identifier_length):
        raise ValueError('ID length must be a positive non-zero power of 2')

    bit_length = identifier_length * 4
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')


def _is_power2(num):
    """
    States if a number is a power of two
    """
    return num != 0 and ((num & (num - 1)) == 0)
