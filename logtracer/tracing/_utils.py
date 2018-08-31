import os
import time
from binascii import hexlify

from google.protobuf.timestamp_pb2 import Timestamp


def post_span(stackdriver_trace_client, span_info):
    """Post span to Stackdriver Trace API."""
    stackdriver_trace_client.create_span(**span_info)


def get_timestamp():
    """Get timestamp in a format Stackdriver Trace accepts it."""
    now = time.time()
    seconds, nanos = to_seconds_and_nanos(now)
    timestamp = Timestamp(seconds=seconds, nanos=nanos)
    return timestamp


def to_seconds_and_nanos(fractional_seconds):
    """Convert fractional seconds to seconds and nanoseconds."""
    seconds = int(fractional_seconds)
    nanos = int((fractional_seconds - seconds) * 10 ** 9)
    return seconds, nanos


def truncate_str(str_to_truncate, limit):
    """Truncate a string if exceed limit and record the truncated bytes count."""
    str_bytes = str_to_truncate.encode('utf-8')
    trunc = {
        'value': str_bytes[:limit].decode('utf-8', errors='ignore'),
        'truncated_byte_count': len(str_bytes) - len(str_bytes[:limit]),
    }
    return trunc


def generate_identifier(identifier_length):
    """
    Generates a new, random identifier in B3 format.
    Arguments:
        identifier_length (int): length of identifier to generate
    Returns:
        (str): A 64-bit random identifier, rendered as a hex String.
    """
    if not is_power2(identifier_length):
        raise ValueError('ID length must be a positive non-zero power of 2')

    bit_length = identifier_length * 4
    byte_length = int(bit_length / 8)
    identifier = os.urandom(byte_length)
    return hexlify(identifier).decode('ascii')


def is_power2(num):
    """
    States if a number is a power of two
    """
    return num != 0 and ((num & (num - 1)) == 0)