"""Code by David Carboni: https://github.com/davidcarboni/B3-Propagation"""

import logging
import os
from binascii import hexlify
from threading import local

logger = logging.getLogger('b3')
logger.setLevel(logging.INFO)

# config
TRACE_LEN = 16
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
    """Get the full current set of B3 values.
    :return: A dict containing the keys "X-B3-TraceId", "X-B3-ParentSpanId", "X-B3-SpanId", "X-B3-Sampled" and
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


def start_span(headers):
    """Collects incoming B3 headers and sets up values for this request as needed.
    The collected/computed values are stored as thread-local data using the defined http header names as keys.
    :param headers: Incoming request headers. These could be http, or part of a GRPC message.
    """
    b3.span = {
        B3_TRACE_ID: headers.get(B3_TRACE_ID) or _generate_identifier(TRACE_LEN),
        B3_PARENT_SPAN_ID: headers.get(B3_PARENT_SPAN_ID),
        B3_SPAN_ID: headers.get(B3_SPAN_ID) or _generate_identifier(SPAN_LEN),
        B3_SAMPLED: headers.get(B3_SAMPLED),
        B3_FLAGS: headers.get(B3_FLAGS)
    }

    logger.debug("Server receive. Starting span" if b3.span[B3_TRACE_ID] else "Starting root span.")
    logger.debug("Resolved B3 values: {values}".format(values=values()))


def end_span():
    """Deletes the span values and logs it."""
    if not hasattr(b3, "span"):
        raise SpanError('`end_span` must be called after `start_span`')
    logger.debug("Client receive. Closing sub-span")
    del b3.span


def generate_subspan_values():
    """ Sets up new span values to contact a downstream service.
    This is used when making a downstream service call. It returns a dict containing the required sub-span headers.
    Each downstream call you make is handled as a new span, so call this every time you need to contact another service.

    For the specification, see: https://github.com/openzipkin/b3-propagation
    :return: A dict containing header values for a downstream request.
    This can be passed directly to e.g. requests.get(...).
    """
    parent = values()
    subspan_values = {
        B3_TRACE_ID: parent[B3_TRACE_ID],
        B3_SPAN_ID: _generate_identifier(SPAN_LEN),
        B3_PARENT_SPAN_ID: parent[B3_SPAN_ID],
    }

    # Propagate only if set:
    if parent[B3_SAMPLED]:
        subspan_values[B3_SAMPLED] = parent[B3_SAMPLED]
    if parent[B3_FLAGS]:
        subspan_values[B3_FLAGS] = parent[B3_FLAGS]

    logger.debug("Client start. Starting sub-span")
    logger.debug("B3 values for sub-span: {b3_headers}".format(b3_headers=values()))

    return subspan_values


def _generate_identifier(identifier_length):
    """
    Generates a new, random identifier in B3 format.
    :return: A 64-bit random identifier, rendered as a hex String.
    """
    bit_length = identifier_length * 4
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')
