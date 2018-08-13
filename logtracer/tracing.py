import os
import time
from binascii import hexlify
from threading import Thread, local

from google.auth.exceptions import DefaultCredentialsError
from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128
TRACE_LEN = 32
SPAN_LEN = 16
B3_TRACE_ID = 'X-B3-TraceId'
B3_PARENT_SPAN_ID = 'X-B3-ParentSpanId'
B3_SPAN_ID = 'X-B3-SpanId'
B3_SAMPLED = 'X-B3-Sampled'
B3_FLAGS = 'X-B3-Flags'
B3_HEADERS = [B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID, B3_SAMPLED, B3_FLAGS]


class TraceException(Exception):
    pass


class StackDriverAuthError(Exception):
    pass


class SpanError(Exception):
    pass


class SpanNotStartedError(Exception):
    pass


class Tracer:
    def __init__(self, json_logger_handler, post_spans_to_stackdriver_api=False):

        self._add_tracer_to_logger_formatter(json_logger_handler)
        self.project_name = json_logger_handler.project_name
        self.service_name = json_logger_handler.service_name
        self.post_spans_to_stackdriver_api = post_spans_to_stackdriver_api
        self._spans = {}
        self.logger = json_logger_handler.get_logger(__name__)
        self._memory = None
        if self.post_spans_to_stackdriver_api:
            try:
                self.trace_client = TraceServiceClient()
            except DefaultCredentialsError:
                raise StackDriverAuthError('Cannot post spans to API, no authentication credentials found.')

    def _add_tracer_to_logger_formatter(self, json_logger_handler):
        json_logger_handler.get_logger(__name__).root.handlers[0].formatter.tracer = self

    def set_logging_level(self, level):
        self.logger.setLevel(level)

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

        span_id = span_values[B3_SPAN_ID]
        self._spans[span_id] = {
            "start_timestamp": _get_timestamp(),
            "display_name": f'{self.service_name}:{request_path}',
            "child_span_count": 0,
            "values": span_values
        }
        self.memory.current_span_id = span_id

        self.logger.debug(f'Span started {self.current_span}')

    @property
    def current_span(self):
        try:
            return self._spans[self.memory.current_span_id]
        except (KeyError, AttributeError):
            raise SpanNotStartedError('No current span found.')

    def delete_current_span(self):
        self.logger.debug(f'Deleting span {self.memory.current_span_id}')
        del self._spans[self.memory.current_span_id]

    def end_traced_span(self, exclude_from_posting=False):
        """
        End a b3 span and collect details about the span, then post it to the API
        (depending on the `_global_vars.post_spans_to_api` flag).
        """

        self.logger.debug(f'Closing span {self.current_span}')

        span_values = self.current_span['values']

        end_timestamp = _get_timestamp()
        if self.post_spans_to_stackdriver_api:
            name = self.trace_client.span_path(self.project_name, span_values[B3_TRACE_ID],
                                               span_values[B3_SPAN_ID])
        else:
            name = f'{self.project_name}/{span_values[B3_TRACE_ID]}/{span_values[B3_SPAN_ID]}'

        span_info = {
            'name': name,
            'span_id': span_values[B3_SPAN_ID],
            'display_name': _truncate_str(self.current_span['display_name'], limit=SPAN_DISPLAY_NAME_BYTE_LIMIT),
            'start_time': self.current_span['start_timestamp'],
            'end_time': end_timestamp,
            'parent_span_id': span_values[B3_PARENT_SPAN_ID],
            'same_process_as_parent_span': BoolValue(value=False),
            'child_span_count': Int32Value(value=self.current_span['child_span_count'])
        }
        if self.post_spans_to_stackdriver_api and not exclude_from_posting:
            post_to_api_job = Thread(target=_post_span, args=(self.trace_client, span_info))
            post_to_api_job.start()

        self.delete_current_span()

    def generate_new_traced_subspan_values(self):
        """
        For use in a one-off downstream call. Use this to generate the values to pass to a downstream service.

        Sets up new span values to contact a downstream service.
        This is used when making a downstream service call. It returns a dict containing the required sub-span headers.
        Each downstream call you make is handled as a new span, so call this every time you need to contact another service.
        Entries with the value `None` are filtered out.

        For the specification, see: https://github.com/openzipkin/b3-propagation

        """
        self.current_span["child_span_count"] += 1
        parent_span_values = self.current_span['values']
        subspan_values = {
            B3_TRACE_ID: parent_span_values[B3_TRACE_ID],
            B3_PARENT_SPAN_ID: parent_span_values[B3_SPAN_ID],
            B3_SPAN_ID: _generate_identifier(SPAN_LEN),
            B3_SAMPLED: parent_span_values[B3_SAMPLED],
            B3_FLAGS: parent_span_values[B3_FLAGS]
        }
        subspan_values = {k: v for k, v in subspan_values.items() if v}
        return subspan_values

    @property
    def memory(self):
        if self._memory is None:
            self._memory = local()
        return self._memory


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
