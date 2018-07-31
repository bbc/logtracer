"""Code based on B3-Propagation by David Carboni: https://github.com/davidcarboni/B3-Propagation"""

import os
from binascii import hexlify
from threading import local

# config
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


def start_span(headers):
    """
    Start a span on an inbound request. Collects incoming B3 headers and sets up values for this request as needed.
    The collected/computed values are stored as thread-local data using the defined http header names as keys.

    Arguments:
        headers: Incoming request headers. These could be http, or part of a GRPC message.

    """
    span_values = {
        B3_TRACE_ID: headers.get(B3_TRACE_ID) or _generate_identifier(TRACE_LEN),
        B3_PARENT_SPAN_ID: headers.get(B3_PARENT_SPAN_ID),
        B3_SPAN_ID: headers.get(B3_SPAN_ID) or _generate_identifier(SPAN_LEN),
        B3_SAMPLED: headers.get(B3_SAMPLED),
        B3_FLAGS: headers.get(B3_FLAGS)
    }

    b3.span = span_values


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
