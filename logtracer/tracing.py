import os
import time
from binascii import hexlify
from threading import Thread, local

from google.auth.exceptions import DefaultCredentialsError
from google.cloud.trace_v2 import TraceServiceClient
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value

from logtracer.exceptions import StackDriverAuthError, SpanNotStartedError
from logtracer.requests_wrapper import RequestsWrapper

SPAN_DISPLAY_NAME_BYTE_LIMIT = 128
TRACE_LEN = 32
SPAN_LEN = 16
B3_TRACE_ID = 'X-B3-TraceId'
B3_PARENT_SPAN_ID = 'X-B3-ParentSpanId'
B3_SPAN_ID = 'X-B3-SpanId'
B3_SAMPLED = 'X-B3-Sampled'
B3_FLAGS = 'X-B3-Flags'
B3_HEADERS = [B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID, B3_SAMPLED, B3_FLAGS]


class Tracer:
    def __init__(self, json_logger_factory, post_spans_to_stackdriver_api=False):
        """
        Class to manage creation and deletion of spans. This should be initialised once within an app then reused
        across it.

        Arguments:
            json_logger_factory (logtracer.jsonlog.JSONLoggerFactory):
                logger factory instance to attach for logging tracing events.
            post_spans_to_stackdriver_api (bool):
                toggle for posting spans to the Stackdriver API (requires google credentials)

        Attributes:
            self.project_name (str): Name of your project, the GCP project name if posting to Stackdriver Trace
            self.service_name (str): Name of your service
            self.logger (logging.Logger): Logger to be used to log trace-related events
            self.requests (logtracer.tracing.RequestsWrapper):
                a wrapper for the `requests` library to conveniently trace outgoing requests

            self._spans (dict): dict to store span information indexed by span id
            self._memory (threading.local()): thread local memory to store the current span ID
            self._post_spans_to_stackdriver_api (bool): toggle for posting spans to Stackdriver API


        """
        self.project_name = json_logger_factory.project_name
        self.service_name = json_logger_factory.service_name
        self.logger = json_logger_factory.get_logger(__name__)
        self.requests = RequestsWrapper(self)
        self.stackdriver_trace_client = None

        self._spans = {}
        self._memory = None
        self._post_spans_to_stackdriver_api = post_spans_to_stackdriver_api

        self._add_tracer_to_logger_formatter(json_logger_factory)
        self._verify_gcp_credentials()

    def _verify_gcp_credentials(self):
        """If the flag is enabled then attempt to load the trace client used for posting spans to the Trace API."""
        if self._post_spans_to_stackdriver_api:
            try:
                self.stackdriver_trace_client = TraceServiceClient()
            except DefaultCredentialsError:
                raise StackDriverAuthError('Cannot post spans to API, no authentication credentials found.')

    def _add_tracer_to_logger_formatter(self, json_logger_factory):
        """Add this instance to the logging formatter to allow the logger to format logs with trace information."""
        json_logger_factory.get_logger().root.handlers[0].formatter.tracer = self

    def set_logging_level(self, level):
        """
        Set the logging level of the tracer

        level (str):
            'DEBUG': Span creation, closure, and deletion information (not useful in production)
            'INFO': Request logging, used by child classes to log incoming and outgoing requests
            'ERROR': Summaries of any errors that have occurred
            'EXCEPTION': Stack traces of any exceptions to have occurred
        """
        self.logger.setLevel(level)

    def start_traced_span(self, incoming_headers, span_name):
        """
        Create a span and set it as the current span in the thread local memory.
        Retrieves span details from inbound call, otherwise generates new values.

        Arguments:
            incoming_headers: Incoming request headers. These could be http, or part of a GRPC message.
            span_name (str): Path of the endpoint of the incoming request.
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
            "display_name": f'{self.service_name}:{span_name}',
            "child_span_count": 0,
            "values": span_values
        }
        self.memory.current_span_id = span_id

        self.logger.debug(f'Span started {self.memory.current_span_id}')

    @property
    def current_span(self):
        """Attempt to return current span data."""
        if self.memory.current_span_id is not None:
            try:
                return self._spans[self.memory.current_span_id]
            except KeyError:
                pass
        raise SpanNotStartedError('No current span found.')

    def start_traced_subspan(self, span_name):
        """Start a traced subspan, for usage with wrapping an unsupported downstream service."""
        subspan_values = self.generate_new_traced_subspan_values()
        self.memory.parent_spans.append(self.memory.current_span_id)
        self.memory.current_span_id = None
        self.start_traced_span(subspan_values, span_name)

    def end_traced_subspan(self, exclude_from_posting=False):
        """Close a traced subspan."""
        self.end_traced_span(exclude_from_posting)
        self.memory.current_span_id = self.memory.parent_spans.pop()

    def end_traced_span(self, exclude_from_posting=False):
        """
        End a span and collect details about the span, then post it to the API.

        Arguments:
            exclude_from_posting (bool): exclude this particular trace from being posted
        """
        self.logger.debug(f'Closing span {self.memory.current_span_id}')

        if self._post_spans_to_stackdriver_api and not exclude_from_posting:
            span_values = self.current_span['values']

            end_timestamp = _get_timestamp()
            if self._post_spans_to_stackdriver_api:
                name = self.stackdriver_trace_client.span_path(self.project_name, span_values[B3_TRACE_ID],
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
            post_to_api_job = Thread(target=_post_span, args=(self.stackdriver_trace_client, span_info))
            post_to_api_job.start()

        self._delete_current_span()

    def _delete_current_span(self):
        """Deletes span details."""
        self.logger.debug(f'Deleting span {self.memory.current_span_id}')
        del self._spans[self.memory.current_span_id]
        self.memory.current_span_id = None

    def generate_new_traced_subspan_values(self):
        """
        For use in a downstream/outbound call. Use this to generate the values to pass to a downstream service.

        If sending outbound requests to a HTTP service using the `requests` library, then use the `self.requests`
        wrapper instead of this function to trace outgoing requests.
        If calling a gRPC service then use the channel interceptor (logtracer.helpers.grpc.interceptors.GRPCTracer)
        instead of this function.

        Entries with the value `None` are filtered out.
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
        """
        Thread local memory for storring the _current_ span, needed for if this class is used in a multi-threaded
        environment.
        """
        if self._memory is None:
            self._memory = local()
            self._memory.current_span_id = None
            self._memory.parent_spans = []
        return self._memory


class SpanContext:
    def __init__(self, tracer, incoming_headers, request_path, exclude_from_posting=False):
        """Context manager for creating a span."""
        self.tracer = tracer
        self.request_path = request_path,
        self.exclude = exclude_from_posting
        self.incoming_headers = incoming_headers

    def __enter__(self):
        self.tracer.start_traced_span(self.incoming_headers, self.request_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracer.end_traced_span(self.exclude)


class SubSpanContext:
    def __init__(self, tracer, request_path, exclude_from_posting=False):
        """Context manager for creating a subspan."""
        self.tracer = tracer
        self.request_path = request_path,
        self.exclude = exclude_from_posting

    def __enter__(self):
        self.tracer.start_traced_subspan(self.request_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracer.end_traced_subspan(self.exclude)


def _post_span(stackdriver_trace_client, span_info):
    """Post span to Stackdriver Trace API."""
    stackdriver_trace_client.create_span(**span_info)


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
