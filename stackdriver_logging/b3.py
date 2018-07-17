"""Code by David Carboni: https://github.com/davidcarboni/B3-Propagation"""

import logging
import os
from functools import wraps
from threading import local

from binascii import hexlify

_log = logging.getLogger('b3')
_log.setLevel(logging.INFO)

# config
DEBUG = False
TRACE_LEN = 16
SPAN_LEN = 16

B3_TRACE_ID = 'X-B3-TraceId'
B3_PARENT_SPAN_ID = 'X-B3-ParentSpanId'
B3_SPAN_ID = 'X-B3-SpanId'
B3_SAMPLED = 'X-B3-Sampled'
B3_FLAGS = 'X-B3-Flags'
B3_HEADERS = [B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID, B3_SAMPLED, B3_FLAGS]

b3 = local()


def values():
    """Get the full current set of B3 values.
    :return: A dict containing the keys "X-B3-TraceId", "X-B3-ParentSpanId", "X-B3-SpanId", "X-B3-Sampled" and
    "X-B3-Flags" for the current span or subspan. NB some of the values are likely be None, but
    all keys will be present.
    """
    result = {}
    try:
        # Check if there's a sub-span in progress, otherwise use the main span, or fall back to an empty hash:
        span = b3.subspan if hasattr(b3, "subspan") else b3.span if hasattr(b3, "span") else {}
        for header in B3_HEADERS:
            result[header] = span.get(header)
    except RuntimeError:
        # We're probably working outside the Application Context at this point, likely on startup:
        # https://stackoverflow.com/questions/31444036/runtimeerror-working-outside-of-application-context
        # We return a dict of empty values so the expected keys are present.
        for header in B3_HEADERS:
            result[header] = None

    return result


def start_span(headers):
    """Collects incoming B3 headers and sets up values for this request as needed.
    The collected/computed values are stored on the application context g using the defined http header names as keys.
    :param headers: Incoming request headers. These could be http, or part of a GRPC message.
    """
    global DEBUG
    b3.span = {}

    trace_id = headers.get(B3_TRACE_ID)
    parent_span_id = headers.get(B3_PARENT_SPAN_ID)
    span_id = headers.get(B3_SPAN_ID)
    sampled = headers.get(B3_SAMPLED)
    flags = headers.get(B3_FLAGS)
    root_span = not trace_id

    # Collect (or generate) a trace ID
    b3.span[B3_TRACE_ID] = trace_id or _generate_identifier(TRACE_LEN)

    # Parent span, if present
    b3.span[B3_PARENT_SPAN_ID] = parent_span_id

    # Collect (or set) the span ID
    b3.span[B3_SPAN_ID] = span_id or _generate_identifier(SPAN_LEN)

    # Collect the "sampled" flag, if present
    # We'll propagate the sampled value unchanged if it's set.
    # We're not currently recording traces to Zipkin, so if it's present, follow the standard and propagate it,
    # otherwise it's better to leave it out, rather than make it "0".
    # This allows downstream services to make a decision if they need to.
    b3.span[B3_SAMPLED] = sampled

    # Set or update the debug setting
    # We'll set it to "1" if debug=True, otherwise we'll propagate it if present.
    b3.span[B3_FLAGS] = "1" if DEBUG else flags

    _info("Server receive. Starting span" if trace_id else "Root span")
    _log.debug("Resolved B3 values: {values}".format(values=values()))


def end_span(response=None):
    """Logs the end of a span.
    This function can be passed to, say, Flask.after_request() if you'd like a log message to confirm the end of a span.
    :param response: Can be None. If this function is passed to Flask.after_request(), this will be passed by the framework.
    :return: the passed-in response parameter is returned without being accessed.
    """
    _end_subspan()
    _info("Server send. Closing span")
    return response


def span(route):
    """Optional decorator for Flask routes.
    If you don't want to trace all routes using `Flask.before_request()' and 'Flask.after_request()'
    you can use this decorator as an alternative way to handle incoming B3 headers:
        @app.route('/instrumented')
        @span
        def instrumented():
            ...
            ...
            ...
    NB @span needs to come after (not before) @app.route.
    """

    @wraps(route)
    def route_decorator(*args, **kwargs):
        start_span()
        try:
            return route(*args, **kwargs)
        finally:
            end_span()

    return route_decorator


class SubSpan:
    """Sub span context manager
    Use a `with...` block when making downstream calls to other services
    in order to propagate trace and span IDs.
    The `__enter__` function returns the necessary headers
    (you can optionally pass in existing headers to be updated).
    Any calls to `values()` whilst in the block will return the subspan IDs:
        with SubSpan([headers]) as headers_b3:
            ... log.debug("Client start: calling downstream service")
            ... requests.get(<downstream service>, headers=headers_b3)
            ... log.debug("Client receive: downstream service responded")
    """

    def __init__(self, headers=None):
        self.headers = headers

    def __enter__(self):
        return _start_subspan(self.headers)

    def __exit__(self, exc_type, exc_val, exc_tb):
        _end_subspan()


def _start_subspan(headers=None):
    """ Sets up a new span to contact a downstream service.
    This is used when making a downstream service call. It returns a dict containing the required sub-span headers.
    Each downstream call you make is handled as a new span, so call this every time you need to contact another service.
    This temporarily updates what's returned by values() to match the sub-span, so it can can also be used when calling
    e.g. a database that doesn't support B3. You'll still be able to record the client side of an interaction,
    even if the downstream server doesn't use the propagated trace information.
    You'll need to call end_subspan when you're done. You can do this using the `SubSpan` class:
        with SubSpan([headers]) as headers_b3:
            ... log.debug("Client start: calling downstream service")
            ... requests.get(<downstream service>, headers=headers_b3)
            ... log.debug("Client receive: downstream service responded")
    For the specification, see: https://github.com/openzipkin/b3-propagation
    :param headers: The headers dict. Headers will be added to this as needed.
    :return: A dict containing header values for a downstream request.
    This can be passed directly to e.g. requests.get(...).
    """
    parent = values()
    b3.subspan = {

        # Propagate the trace ID
        B3_TRACE_ID: parent[B3_TRACE_ID],

        # Start a new span for the outgoing request
        B3_SPAN_ID: _generate_identifier(SPAN_LEN),

        # Set the current span as the parent span
        B3_PARENT_SPAN_ID: parent[B3_SPAN_ID],

        B3_SAMPLED: parent[B3_SAMPLED],
        B3_FLAGS: parent[B3_FLAGS],
    }

    # Set up headers
    # NB dict() ensures we don't alter the value passed in. Maybe that's too conservative?
    result = dict(headers or {})
    result.update({
        B3_TRACE_ID: b3.subspan[B3_TRACE_ID],
        B3_SPAN_ID: b3.subspan[B3_SPAN_ID],
        B3_PARENT_SPAN_ID: b3.subspan[B3_PARENT_SPAN_ID],
    })

    # Propagate only if set:
    if b3.subspan[B3_SAMPLED]:
        result[B3_SAMPLED] = b3.subspan[B3_SAMPLED]
    if b3.subspan[B3_FLAGS]:
        result[B3_FLAGS] = b3.subspan[B3_FLAGS]

    _info("Client start. Starting sub-span")
    _log.debug("B3 values for sub-span: {b3_headers}".format(b3_headers=values()))
    _log.debug("All headers for downstream request: {b3_headers}".format(b3_headers=result))

    return result


def _end_subspan():
    """ Removes the headers for a sub-span.
    You should call this in e.g. a finally block when you have finished making a downstream service call.
    For the specification, see: https://github.com/openzipkin/b3-propagation
    """
    if hasattr(b3, "subspan"):
        _info("Client receive. Closing sub-span")
        delattr(b3, "subspan")


def _generate_identifier(identifier_length):
    """
    Generates a new, random identifier in B3 format.
    :return: A 64-bit random identifier, rendered as a hex String.
    """
    bit_length = identifier_length * 4
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')


def _info(message):
    """Convenience function to log current span values.
    """
    span = values()
    _log.info(message + ": {span} in trace {trace}. (Parent span: {parent}).".format(
        span=span.get(B3_SPAN_ID),
        trace=span.get(B3_TRACE_ID),
        parent=span.get(B3_PARENT_SPAN_ID),
    ))
