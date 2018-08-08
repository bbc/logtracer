from unittest.mock import patch, MagicMock

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value
from pytest import fixture

from logtracer import _global_vars
from logtracer.tracing import configure_tracing, StackDriverAuthError, start_traced_span, \
    end_traced_span, _post_span, generate_new_traced_subspan_values, TraceException, _truncate_str, _get_timestamp, \
    _to_seconds_and_nanos, B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID


@fixture
def thread_memory():
    with patch('logtracer.tracing.thread_memory') as thread_memory:
        yield thread_memory


@patch('logtracer.tracing.TraceServiceClient', MagicMock())
def test_configure_tracing_post_with_creds():
    configure_tracing(post_spans_to_stackdriver_api=True)

    assert _global_vars.post_spans_to_stackdriver_api

    # import after global is set
    from logtracer.tracing import trace_client
    assert trace_client is not None


@patch('logtracer.tracing.TraceServiceClient', MagicMock(side_effect=DefaultCredentialsError))
def test_configure_tracing_post_without_creds():
    with pytest.raises(StackDriverAuthError):
        configure_tracing(post_spans_to_stackdriver_api=True)


@patch('logtracer.tracing.TraceServiceClient', MagicMock())
def test_configure_tracing_no_post_with_creds():
    configure_tracing(post_spans_to_stackdriver_api=False)

    from logtracer.tracing import trace_client
    assert trace_client is not None
    assert not _global_vars.post_spans_to_stackdriver_api


@patch('logtracer.tracing.TraceServiceClient', MagicMock(side_effect=DefaultCredentialsError))
def test_configure_tracing_no_post_without_creds():
    configure_tracing(post_spans_to_stackdriver_api=False)

    from logtracer.tracing import trace_client
    assert trace_client is not None
    assert not _global_vars.post_spans_to_stackdriver_api


@patch('logtracer.tracing._b3')
@patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_timestamp'))
def test_start_traced_span(m_b3, thread_memory):
    _global_vars.service_name = 'test_service'
    start_traced_span({"incoming": "headers"}, '/request/path')
    expected_span = {
        'start_timestamp': 'test_timestamp',
        'display_name': 'test_service:/request/path',
        'child_span_count': 0
    }

    assert thread_memory.span == expected_span
    m_b3.start_span.assert_called_with({"incoming": "headers"})


@patch('logtracer.tracing._b3')
@patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_end_timestamp'))
@patch('logtracer.tracing.trace_client')
@patch('logtracer.tracing.Thread')
@patch('logtracer.tracing._truncate_str', return_value='truncated_str')
def test_end_traced_span_post(m_truncate, m_thread, m_trace_client, m_b3, thread_memory):
    m_b3.B3_SPAN_ID = B3_SPAN_ID
    m_b3.B3_PARENT_SPAN_ID = B3_PARENT_SPAN_ID
    m_b3.B3_TRACE_ID = B3_TRACE_ID
    m_b3.values.return_value = {
        B3_SPAN_ID: "test_span_id",
        B3_PARENT_SPAN_ID: "test_parent_span_id",
        B3_TRACE_ID: "test_trace_id"
    }
    m_trace_client.span_path.return_value = "span_name"
    _global_vars.post_spans_to_stackdriver_api = True
    _global_vars.gcp_project_name = 'test_project_name'
    thread_memory.span = {
        'display_name': 'test_display_name',
        'start_timestamp': 'test_start_timestamp',
        'child_span_count': 100
    }

    end_traced_span()

    m_trace_client.span_path.assert_called_with('test_project_name', 'test_trace_id', 'test_span_id')
    m_truncate.assert_called_with('test_display_name', limit=128)
    expected_span_info = {
        'name': 'span_name',
        'span_id': 'test_span_id',
        'display_name': 'truncated_str',
        'start_time': 'test_start_timestamp',
        'end_time': 'test_end_timestamp',
        'parent_span_id': 'test_parent_span_id',
        'same_process_as_parent_span': BoolValue(value=False),
        'child_span_count': Int32Value(value=100)
    }
    m_thread.assert_called_with(target=_post_span, args=(expected_span_info,))
    assert m_b3.end_span.called
    assert not hasattr(thread_memory, 'span')


@patch('logtracer.tracing._b3')
@patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_end_timestamp'))
@patch('logtracer.tracing.trace_client', MagicMock())
@patch('logtracer.tracing.Thread')
@patch('logtracer.tracing.BoolValue', MagicMock())
@patch('logtracer.tracing.Int32Value', MagicMock())
@patch('logtracer.tracing._truncate_str', MagicMock(return_value='truncated_str'))
def test_end_traced_span_no_post(m_thread, m_b3, thread_memory):
    _global_vars.post_spans_to_stackdriver_api = False
    thread_memory.span = MagicMock()

    end_traced_span()

    assert not m_thread.called
    assert m_b3.end_span.called
    assert not hasattr(thread_memory, 'span')


@patch('logtracer.tracing.generate_new_subspan_values')
def test_generate_new_traced_subspan_values(m_generate, thread_memory):
    thread_memory.span = {
        "child_span_count": 0
    }
    generate_new_traced_subspan_values()

    assert thread_memory.span['child_span_count'] == 1
    assert m_generate.called


def test_generate_new_traced_subspan_values_no_span_started():
    with pytest.raises(TraceException):
        generate_new_traced_subspan_values()


@patch('logtracer.tracing.trace_client')
def test_post_span(m_trace_client):
    _post_span({"info": "test_span_info"})
    m_trace_client.create_span.assert_called_with(info="test_span_info")


@patch('logtracer.tracing._to_seconds_and_nanos')
@patch('logtracer.tracing.time')
def test_get_timestamp(m_time, m_to_secs_and_nanos):
    m_time.time.return_value = 'test_time'
    m_to_secs_and_nanos.return_value = (100, 200)

    timestamp = _get_timestamp()

    m_to_secs_and_nanos.assert_called_with('test_time')
    assert timestamp == Timestamp(seconds=100, nanos=200)


def test_to_seconds_and_nanos():
    seconds, nanos = _to_seconds_and_nanos(1532962140.8755891)

    assert seconds == 1532962140
    assert nanos == 875589132


def test_truncate_str():
    shortstr = 'short'
    trunc_obj = _truncate_str(shortstr, limit=10)
    assert trunc_obj == {'value': 'short', 'truncated_byte_count': 0}

    longstr = 'kindoflongstring'
    trunc_obj = _truncate_str(longstr, limit=10)
    assert trunc_obj == {'value': 'kindoflong', 'truncated_byte_count': 6}
