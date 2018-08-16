import time
from random import randint
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue, Int32Value
from pytest import fixture

from logtracer.exceptions import StackDriverAuthError, SpanNotStartedError
from logtracer.requests_wrapper import RequestsWrapper
from logtracer.tracing import Tracer, _post_span, _get_timestamp, _to_seconds_and_nanos, _truncate_str, SpanContext, \
    SubSpanContext

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


test_span_headers = {
    'X-B3-TraceId': 'test_trace_id',
    'X-B3-ParentSpanId': 'test_parent_span_id',
    'X-B3-SpanId': 'test_span_id',
    'X-B3-Sampled': 'test_sampled',
    'X-B3-Flags': 'test_b3_flags'
}


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
    tracer.current_span = ''

    tracer.start_traced_span(test_span_headers, 'test_span_name')

    expected_spans = {
        'test_span_id': {
            "start_timestamp": 'test_timestamp',
            "display_name": 'test_service_name:test_span_name',
            "child_span_count": 0,
            "values": test_span_headers
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


def test_tracer_start_traced_subspan_without_span(tracer):
    tracer.memory.current_span_id = None
    with pytest.raises(SpanNotStartedError):
        tracer.start_traced_subspan('test_span_name')


def test_tracer_end_traced_subspan(tracer):
    tracer.end_traced_span = MagicMock()
    tracer.memory.parent_spans = ['test_parent_span_id']
    tracer.memory.current_span_id = 'test_current_span_id'

    tracer.end_traced_subspan('test_exclude_bool')

    assert tracer.memory.current_span_id == 'test_parent_span_id'
    assert tracer.memory.parent_spans == []
    tracer.end_traced_span.assert_called_with('test_exclude_bool')


test_span_info = {
    'values': test_span_headers,
    'display_name': 'test_display_name',
    'start_timestamp': 'test_start_time',
    'child_span_count': 0
}


@patch(CLASS_PATH + 'current_span', test_span_info)
@patch(MODULE_PATH + '_get_timestamp', MagicMock(return_value='test_timestamp'))
@patch(MODULE_PATH + '_truncate_str', MagicMock(return_value='test_truncated_str'))
@patch(MODULE_PATH + 'Thread')
def test_tracer_end_traced_span_do_post(m_thread, tracer):
    tracer.memory.current_span_id = 'test_span_id'
    tracer._post_spans_to_stackdriver_api = True
    tracer.stackdriver_trace_client = MagicMock()
    tracer.stackdriver_trace_client.span_path.return_value = 'test_span_name'
    tracer._delete_current_span = MagicMock()

    tracer.end_traced_span(exclude_from_posting=False)

    tracer.logger.debug.assert_called_with(
        "Closing span test_span_id")
    tracer.stackdriver_trace_client.span_path.assert_called_with('test_project_name', 'test_trace_id', 'test_span_id')

    expected_span_info = {
        'name': 'test_span_name',
        'span_id': 'test_span_id',
        'display_name': 'test_truncated_str',
        'start_time': 'test_start_time',
        'end_time': 'test_timestamp',
        'parent_span_id': 'test_parent_span_id',
        'same_process_as_parent_span': BoolValue(value=False),
        'child_span_count': Int32Value(value=0)
    }
    m_thread.assert_called_with(target=_post_span, args=(tracer.stackdriver_trace_client, expected_span_info,))
    assert tracer._delete_current_span.called


@patch(CLASS_PATH + 'current_span', test_span_info)
@patch(MODULE_PATH + '_get_timestamp', MagicMock(return_value='test_timestamp'))
@patch(MODULE_PATH + '_truncate_str', MagicMock(return_value='test_truncated_str'))
@patch(MODULE_PATH + 'Thread')
def test_tracer_end_traced_span_dont_post(m_thread, tracer):
    tracer.memory.current_span_id = 'test_span_id'
    tracer._post_spans_to_stackdriver_api = False
    tracer._delete_current_span = MagicMock()
    tracer.stackdriver_trace_client = MagicMock()

    tracer.end_traced_span(exclude_from_posting=False)

    tracer.logger.debug.assert_called_with("Closing span test_span_id")
    assert not tracer.stackdriver_trace_client.called
    assert not m_thread.called
    assert tracer._delete_current_span.called


def test_tracer_delete_current_span(tracer):
    tracer.memory.current_span_id = 'test_current_span_id'
    tracer._spans = {'test_current_span_id': 'test_span'}

    tracer._delete_current_span()

    tracer.logger.debug.assert_called_with('Deleting span test_current_span_id')
    assert tracer._spans == {}
    assert tracer.memory.current_span_id is None


@patch(CLASS_PATH + 'current_span', test_span_info)
@patch(MODULE_PATH + '_generate_identifier', lambda n: f'test_generated_id_{n}')
def test_tracer_generate_new_traced_subspan_values(tracer):
    subspan_values = tracer.generate_new_traced_subspan_values()

    expected_subspan_values = {
        'X-B3-Flags': 'test_b3_flags',
        'X-B3-ParentSpanId': 'test_span_id',
        'X-B3-Sampled': 'test_sampled',
        'X-B3-SpanId': 'test_generated_id_16',
        'X-B3-TraceId': 'test_trace_id'
    }
    assert subspan_values == expected_subspan_values
    assert tracer.current_span['child_span_count'] == 1


@patch(CLASS_PATH + '_add_tracer_to_logger_formatter', MagicMock())
@patch(CLASS_PATH + '_verify_gcp_credentials', MagicMock())
@patch(CLASS_PATH + 'memory', MagicMock())
def test_tracer_memory():
    m_json_logger_factory = MagicMock(name='json_logger_factory')
    m_json_logger_factory.project_name = 'test_project_name'
    m_json_logger_factory.service_name = 'test_service_name'
    tracer = Tracer(m_json_logger_factory)

    tracer.memory.test = 'test'

    def test_threaded_memory(tracer, asserts):
        asserts.append(tracer.memory.test == 'test')
        rand_str = f'test{randint(100)}'
        tracer.memory.test = rand_str
        time.sleep(randint(2))
        asserts.append(tracer.memory.test == rand_str)

    asserts = []
    threads = [Thread(target=test_threaded_memory, args=(tracer, asserts)) for _ in range(20)]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert all(asserts)
    assert tracer.memory.test == 'test'


def test_spancontext():
    m_tracer = MagicMock()
    with SpanContext(m_tracer, {'test': 'headers'}, 'test_span_name', exclude_from_posting='test_exclude_bool'):
        m_tracer.start_traced_span.assert_called_with({'test': 'headers'}, 'test_span_name')
        assert not m_tracer.end_traced_span.called
    m_tracer.end_traced_span.assert_called_with('test_exclude_bool')


def test_subspancontext_no_span():
    m_tracer = MagicMock()
    m_tracer.start_traced_subspan.side_effect = SpanNotStartedError
    with pytest.raises(SpanNotStartedError):
        with SubSpanContext(m_tracer, 'test_span_name', 'test_exclude_bool'):
            pass


def test_post_span():
    m_trace_client = MagicMock()
    _post_span(m_trace_client, {"info": "test_span_info"})
    m_trace_client.create_span.assert_called_with(info="test_span_info")


@patch(MODULE_PATH + '_to_seconds_and_nanos')
@patch(MODULE_PATH + 'time')
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
