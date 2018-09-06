from unittest.mock import MagicMock, patch

from google.protobuf.timestamp_pb2 import Timestamp

from logtracer.tracing._utils import post_span, get_timestamp, to_seconds_and_nanos, truncate_str

MODULE_PATH = 'logtracer.tracing._utils.'


def test_post_span():
    m_trace_client = MagicMock()
    post_span(m_trace_client, {"info": "test_span_info"})
    m_trace_client.create_span.assert_called_with(info="test_span_info")


@patch(MODULE_PATH + 'to_seconds_and_nanos')
@patch(MODULE_PATH + 'time')
def test_get_timestamp(m_time, m_to_secs_and_nanos):
    m_time.time.return_value = 'test_time'
    m_to_secs_and_nanos.return_value = (100, 200)

    timestamp = get_timestamp()

    m_to_secs_and_nanos.assert_called_with('test_time')
    assert timestamp == Timestamp(seconds=100, nanos=200)


def test_to_seconds_and_nanos():
    seconds, nanos = to_seconds_and_nanos(1532962140.8755891)

    assert seconds == 1532962140
    assert nanos == 875589132


def test_truncate_str():
    shortstr = 'short'
    trunc_obj = truncate_str(shortstr, limit=10)
    assert trunc_obj == {'value': 'short', 'truncated_byte_count': 0}

    longstr = 'kindoflongstring'
    trunc_obj = truncate_str(longstr, limit=10)
    assert trunc_obj == {'value': 'kindoflong', 'truncated_byte_count': 6}
