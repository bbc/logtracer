from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError
from pytest import fixture

from logtracer.exceptions import StackDriverAuthError, SpanNotStartedError
from logtracer.requests_wrapper import RequestsWrapper
from logtracer.tracing import Tracer

CLASS_PATH = 'logtracer.tracing.Tracer.'
MODULE_PATH = 'logtracer.tracing.'


@fixture
def tracer():
    m_json_logger_factory = MagicMock(name='json_logger_factory')
    m_json_logger_factory.project_name = 'test_project_name'
    m_json_logger_factory.service_name = 'test_service_name'

    with patch(CLASS_PATH + '_add_tracer_to_logger_formatter', MagicMock()), \
         patch(CLASS_PATH + '_verify_gcp_credentials', MagicMock()), \
         patch(CLASS_PATH + 'memory', MagicMock()):
        tracer = Tracer(m_json_logger_factory)
        yield tracer


def test_tracer_init(tracer):
    assert tracer.project_name == 'test_project_name'
    assert tracer.service_name == 'test_service_name'
    assert 'json_logger_factory.get_logger()' in repr(tracer.logger)
    assert isinstance(tracer.requests, RequestsWrapper)

    assert tracer._spans == {}
    assert tracer._memory is None
    assert tracer._post_spans_to_stackdriver_api is False

    assert tracer._verify_gcp_credentials.called
    assert tracer._add_tracer_to_logger_formatter.called


def test_tracer_verify_gcp_credentials_false():
    m_tracer = MagicMock()
    m_tracer._post_spans_to_stackdriver_api = False
    m_tracer.stackdriver_trace_client = 'not_set'
    Tracer._verify_gcp_credentials(m_tracer)

    assert m_tracer.stackdriver_trace_client == 'not_set'


@patch(MODULE_PATH + 'TraceServiceClient', MagicMock(return_value='test_trace_service_client'))
def test_tracer_verify_gcp_credentials_true_success():
    m_tracer = MagicMock()
    m_tracer._post_spans_to_stackdriver_api = True
    Tracer._verify_gcp_credentials(m_tracer)

    assert m_tracer.stackdriver_trace_client == 'test_trace_service_client'


@patch(MODULE_PATH + 'TraceServiceClient', MagicMock(side_effect=DefaultCredentialsError))
def test_tracer_verify_gcp_credentials_true_fail():
    m_tracer = MagicMock()
    m_tracer._post_spans_to_stackdriver_api = True
    with pytest.raises(StackDriverAuthError):
        Tracer._verify_gcp_credentials(m_tracer)


def test_tracer_add_tracer_to_logger_formatter():
    m_tracer, m_logger_factory = MagicMock(), MagicMock()
    Tracer._add_tracer_to_logger_formatter(m_tracer, m_logger_factory)

    assert m_logger_factory.get_logger().root.handlers[0].formatter.tracer == m_tracer


def test_tracer_set_logging_level(tracer):
    tracer.set_logging_level('test_level')
    assert tracer.logger.setLevel.called_with_args('test_level')


@patch(MODULE_PATH + '_generate_identifier', lambda n: f'test_generated_id_{n}')
@patch(MODULE_PATH + '_get_timestamp', MagicMock(return_value='test_timestamp'))
@patch(CLASS_PATH + 'current_span', 'test_current_span')
def test_tracer_start_traced_span_with_headers(tracer):
    headers = {
        'X-B3-TraceId': 'test_trace_id',
        'X-B3-ParentSpanId': 'test_parent_span_id',
        'X-B3-SpanId': 'test_span_id',
        'X-B3-Sampled': 'test_sampled',
        'X-B3-Flags': 'test_b3_flags'
    }

    tracer.current_span = ''

    tracer.start_traced_span(headers, 'test_span_name')

    expected_spans = {
        'test_span_id': {
            "start_timestamp": 'test_timestamp',
            "display_name": 'test_service_name:test_span_name',
            "child_span_count": 0,
            "values": headers
        }
    }
    assert tracer._spans == expected_spans
    assert tracer.memory.current_span_id == 'test_span_id'
    assert tracer.logger.debug.called_with_args('Span started test_current_span')


@patch(MODULE_PATH + '_generate_identifier', lambda n: f'test_generated_id_{n}')
@patch(MODULE_PATH + '_get_timestamp', MagicMock(return_value='test_timestamp'))
@patch(CLASS_PATH + 'current_span', 'test_current_span')
def test_tracer_start_traced_span_without_headers(tracer):
    headers = {}
    tracer.current_span = ''

    tracer.start_traced_span(headers, 'test_span_name')

    expected_spans = {
        'test_generated_id_16': {
            "start_timestamp": 'test_timestamp',
            "display_name": 'test_service_name:test_span_name',
            "child_span_count": 0,
            "values": {
                'X-B3-Flags': None,
                'X-B3-ParentSpanId': None,
                'X-B3-Sampled': None,
                'X-B3-SpanId': 'test_generated_id_16',
                'X-B3-TraceId': 'test_generated_id_32'
            }
        }
    }
    assert tracer._spans == expected_spans
    assert tracer.memory.current_span_id == 'test_generated_id_16'
    assert tracer.logger.debug.called_with_args('Span started test_current_span')


def test_tracer_current_span(tracer):
    tracer.memory.current_span_id = 'test_span_id'
    tracer._spans = {
        'test_span_id': 'test_span'
    }
    current = tracer.current_span

    assert current == 'test_span'


def test_tracer_current_span_fail(tracer):
    tracer.memory.current_span_id = 'test_span_id'
    tracer._spans = {
        'non_matching_span': 'test_span'
    }
    with pytest.raises(SpanNotStartedError):
        tracer.current_span


@patch(CLASS_PATH + 'generate_new_traced_subspan_values', MagicMock(return_value='test_new_subspan_values'))
def test_tracer_start_traced_subspan(tracer):
    tracer.memory.current_span_id = 'test_current_span_id'
    tracer.memory.parent_spans = []
    tracer.start_traced_span = MagicMock()

    tracer.start_traced_subspan('test_span_name')

    assert tracer.memory.parent_spans == ['test_current_span_id']
    assert tracer.memory.current_span_id is None
    tracer.start_traced_span.assert_called_with('test_new_subspan_values', 'test_span_name')


def test_tracer_end_traced_subspan(tracer):
    tracer.end_traced_span = MagicMock()
    tracer.memory.parent_spans = ['test_parent_span_id']
    tracer.memory.current_span_id = 'test_current_span_id'

    tracer.end_traced_subspan('test_exclude_bool')

    assert tracer.memory.current_span_id == 'test_parent_span_id'
    assert tracer.memory.parent_spans == []
    tracer.end_traced_span.assert_called_with('test_exclude_bool')


def test_tracer_end_traced_span():
    pass

#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# @patch('logtracer.tracing.TraceServiceClient', MagicMock())
# def test_configure_tracing_post_with_creds():
#     configure_tracing(post_spans_to_stackdriver_api=True)
#
#     assert _global_vars.post_spans_to_stackdriver_api
#
#     # import after global is set
#     from logtracer.tracing import trace_client
#     assert trace_client is not None
#
#
# @patch('logtracer.tracing.TraceServiceClient', MagicMock(side_effect=DefaultCredentialsError))
# def test_configure_tracing_post_without_creds():
#     with pytest.raises(StackDriverAuthError):
#         configure_tracing(post_spans_to_stackdriver_api=True)
#
#
# @patch('logtracer.tracing.TraceServiceClient', MagicMock())
# def test_configure_tracing_no_post_with_creds():
#     configure_tracing(post_spans_to_stackdriver_api=False)
#
#     from logtracer.tracing import trace_client
#     assert trace_client is not None
#     assert not _global_vars.post_spans_to_stackdriver_api
#
#
# @patch('logtracer.tracing.TraceServiceClient', MagicMock(side_effect=DefaultCredentialsError))
# def test_configure_tracing_no_post_without_creds():
#     configure_tracing(post_spans_to_stackdriver_api=False)
#
#     from logtracer.tracing import trace_client
#     assert trace_client is not None
#     assert not _global_vars.post_spans_to_stackdriver_api
#
#
# @patch('logtracer.tracing._b3')
# @patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_timestamp'))
# def test_start_traced_span(m_b3, thread_memory):
#     _global_vars.service_name = 'test_service'
#     start_traced_span({"incoming": "headers"}, '/request/path')
#     expected_span = {
#         'start_timestamp': 'test_timestamp',
#         'display_name': 'test_service:/request/path',
#         'child_span_count': 0
#     }
#
#     assert thread_memory.span == expected_span
#     m_b3.start_span.assert_called_with({"incoming": "headers"})
#
#
# @patch('logtracer.tracing._b3')
# @patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_end_timestamp'))
# @patch('logtracer.tracing.trace_client')
# @patch('logtracer.tracing.Thread')
# @patch('logtracer.tracing._truncate_str', return_value='truncated_str')
# def test_end_traced_span_post(m_truncate, m_thread, m_trace_client, m_b3, thread_memory):
#     m_b3.B3_SPAN_ID = B3_SPAN_ID
#     m_b3.B3_PARENT_SPAN_ID = B3_PARENT_SPAN_ID
#     m_b3.B3_TRACE_ID = B3_TRACE_ID
#     m_b3.values.return_value = {
#         B3_SPAN_ID: "test_span_id",
#         B3_PARENT_SPAN_ID: "test_parent_span_id",
#         B3_TRACE_ID: "test_trace_id"
#     }
#     m_trace_client.span_path.return_value = "span_name"
#     _global_vars.post_spans_to_stackdriver_api = True
#     _global_vars.gcp_project_name = 'test_project_name'
#     thread_memory.span = {
#         'display_name': 'test_display_name',
#         'start_timestamp': 'test_start_timestamp',
#         'child_span_count': 100
#     }
#
#     end_traced_span()
#
#     m_trace_client.span_path.assert_called_with('test_project_name', 'test_trace_id', 'test_span_id')
#     m_truncate.assert_called_with('test_display_name', limit=128)
#     expected_span_info = {
#         'name': 'span_name',
#         'span_id': 'test_span_id',
#         'display_name': 'truncated_str',
#         'start_time': 'test_start_timestamp',
#         'end_time': 'test_end_timestamp',
#         'parent_span_id': 'test_parent_span_id',
#         'same_process_as_parent_span': BoolValue(value=False),
#         'child_span_count': Int32Value(value=100)
#     }
#     m_thread.assert_called_with(target=_post_span, args=(expected_span_info,))
#     assert m_b3.end_span.called
#     assert not hasattr(thread_memory, 'span')
#
#
# @patch('logtracer.tracing._b3')
# @patch('logtracer.tracing._get_timestamp', MagicMock(return_value='test_end_timestamp'))
# @patch('logtracer.tracing.trace_client', MagicMock())
# @patch('logtracer.tracing.Thread')
# @patch('logtracer.tracing.BoolValue', MagicMock())
# @patch('logtracer.tracing.Int32Value', MagicMock())
# @patch('logtracer.tracing._truncate_str', MagicMock(return_value='truncated_str'))
# def test_end_traced_span_no_post(m_thread, m_b3, thread_memory):
#     _global_vars.post_spans_to_stackdriver_api = False
#     thread_memory.span = MagicMock()
#
#     end_traced_span()
#
#     assert not m_thread.called
#     assert m_b3.end_span.called
#     assert not hasattr(thread_memory, 'span')
#
#
# @patch('logtracer.tracing.generate_new_subspan_values')
# def test_generate_new_traced_subspan_values(m_generate, thread_memory):
#     thread_memory.span = {
#         "child_span_count": 0
#     }
#     generate_new_traced_subspan_values()
#
#     assert thread_memory.span['child_span_count'] == 1
#     assert m_generate.called
#
#
# def test_generate_new_traced_subspan_values_no_span_started():
#     with pytest.raises(TraceException):
#         generate_new_traced_subspan_values()
#
#
# @patch('logtracer.tracing.trace_client')
# def test_post_span(m_trace_client):
#     _post_span({"info": "test_span_info"})
#     m_trace_client.create_span.assert_called_with(info="test_span_info")
#
#
# @patch('logtracer.tracing._to_seconds_and_nanos')
# @patch('logtracer.tracing.time')
# def test_get_timestamp(m_time, m_to_secs_and_nanos):
#     m_time.time.return_value = 'test_time'
#     m_to_secs_and_nanos.return_value = (100, 200)
#
#     timestamp = _get_timestamp()
#
#     m_to_secs_and_nanos.assert_called_with('test_time')
#     assert timestamp == Timestamp(seconds=100, nanos=200)
#
#
# def test_to_seconds_and_nanos():
#     seconds, nanos = _to_seconds_and_nanos(1532962140.8755891)
#
#     assert seconds == 1532962140
#     assert nanos == 875589132
#
#
# def test_truncate_str():
#     shortstr = 'short'
#     trunc_obj = _truncate_str(shortstr, limit=10)
#     assert trunc_obj == {'value': 'short', 'truncated_byte_count': 0}
#
#     longstr = 'kindoflongstring'
#     trunc_obj = _truncate_str(longstr, limit=10)
#     assert trunc_obj == {'value': 'kindoflong', 'truncated_byte_count': 6}
