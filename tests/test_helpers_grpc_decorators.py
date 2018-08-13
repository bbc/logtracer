from unittest.mock import MagicMock, patch, call

import pytest

from logtracer.helpers.grpc.decorators import trace_call, trace_all_calls
from logtracer.helpers.grpc.redact import _rsetattr, _rgetattr, redact_request


def test_rsetattr():
    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr', 'test_val')
    assert m_obj.test_attr == 'test_val'

    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr1.test_attr2', 'test_val')
    assert m_obj.test_attr1.test_attr2 == 'test_val'

    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr1.test_attr2.test_attr3', 'test_val')
    assert m_obj.test_attr1.test_attr2.test_attr3 == 'test_val'


def test_rgetattr():
    m_obj = object()
    with pytest.raises(AttributeError):
        _rgetattr(m_obj, 'test_attr')

    m_obj = MagicMock()
    m_obj.test_attr1 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1') == 'test_val'

    m_obj = MagicMock()
    m_obj.test_attr1.test_attr2 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1.test_attr2') == 'test_val'

    m_obj = MagicMock()
    m_obj.test_attr1.test_attr2.test_attr3 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1.test_attr2.test_attr3') == 'test_val'


def test_redact_request():
    m_request = MagicMock()
    m_request.test_sensitive_field = 'sensitive_val'
    m_request.test_unsensitive_field = 'unsensitive_val'
    m_request.test_nested.test_sensitive_field = 'sensitive_val'
    m_request.test_nested.test_field = 'unsensitive_val'

    redacted = redact_request(m_request, ['test_sensitive_field', 'test_nested.test_sensitive_field'])

    assert m_request.test_sensitive_field == 'sensitive_val'
    assert m_request.test_unsensitive_field == 'unsensitive_val'
    assert m_request.test_nested.test_sensitive_field == 'sensitive_val'
    assert m_request.test_nested.test_field == 'unsensitive_val'

    assert redacted.test_sensitive_field == 'REDACTED'
    assert redacted.test_unsensitive_field == 'unsensitive_val'
    assert redacted.test_nested.test_sensitive_field == 'REDACTED'
    assert redacted.test_nested.test_field == 'unsensitive_val'


@patch('logtracer.helpers.grpc.decorators.get_logger')
@patch('logtracer.helpers.grpc.decorators.start_traced_span')
@patch('logtracer.helpers.grpc.decorators.end_traced_span')
@patch('logtracer.helpers.grpc.decorators.redact_request')
def test_trace_call(m_redact_request, m_end_traced_span, m_start_traced_span, m_get_logger):
    m_traced_method, m_self, m_logger, m_context, m_request, m_response = [MagicMock()] * 6
    m_traced_method.__name__ = 'test_traced_method_name'
    m_traced_method.return_value = m_response
    m_get_logger.return_value = m_logger
    m_request.b3_values = 'test_b3_values'
    m_redact_request.return_value = 'test_redacted_request'

    trace_call_decorater = trace_call('test_redacted_fields')
    log_span = trace_call_decorater(m_traced_method)
    response = log_span(m_self, m_request, m_context)

    m_start_traced_span.assert_called_with('test_b3_values', 'test_traced_method_name')
    m_redact_request.assert_called_with(m_request, 'test_redacted_fields')
    expected_logs = [
        call("gRPC - Call 'test_traced_method_name': test_redacted_request"),
        call("gRPC - Return 'test_traced_method_name'"),
    ]
    m_traced_method.assert_called_with(m_self, m_request, m_context)
    assert m_logger.info.call_args_list == expected_logs
    assert m_end_traced_span.called
    assert response == m_response


@patch('logtracer.helpers.grpc.decorators.get_logger')
@patch('logtracer.helpers.grpc.decorators.start_traced_span')
@patch('logtracer.helpers.grpc.decorators.end_traced_span')
@patch('logtracer.helpers.grpc.decorators.redact_request')
def test_trace_call_exception(m_redact_request, m_end_traced_span, m_start_traced_span, m_get_logger):
    m_traced_method, m_self, m_logger, m_context, m_request = [MagicMock()] * 5
    m_traced_method.__name__ = 'test_traced_method_name'
    m_exception = Exception('test_exception_message')
    m_traced_method.side_effect = m_exception
    m_get_logger.return_value = m_logger
    m_request.b3_values = 'test_b3_values'
    m_redact_request.return_value = 'test_redacted_request'

    trace_call_decorater = trace_call('test_redacted_fields')
    log_span = trace_call_decorater(m_traced_method)
    with pytest.raises(Exception):
        log_span(m_self, m_request, m_context)

    m_start_traced_span.assert_called_with('test_b3_values', 'test_traced_method_name')
    m_logger.info.assert_called_with("gRPC - Call 'test_traced_method_name': test_redacted_request")
    m_redact_request.assert_called_with(m_request, 'test_redacted_fields')
    m_traced_method.assert_called_with(m_self, m_request, m_context)
    m_logger.exception.assert_called_with(m_exception)
    m_logger.error.assert_called_with("gRPC - Exception - 'test_traced_method_name'")
    assert m_end_traced_span.called


@patch('logtracer.helpers.grpc.decorators.trace_call')
def test_trace_all_calls(m_trace_call):
    class MockGRPCClass:
        def __init__(self):
            pass

        def mock_method(self):
            pass

        @property
        def mock_property(self):
            pass

    m_trace_call_decorator = MagicMock(name='trace_call_decorator')
    m_trace_call.return_value = m_trace_call_decorator

    decorate = trace_all_calls('test_redacted_fields')
    decorate(MockGRPCClass)

    assert 'trace_call_decorator' in repr(MockGRPCClass.mock_method)
    assert 'trace_call_decorator' not in repr(MockGRPCClass.mock_property)
    assert 'trace_call_decorator' not in repr(MockGRPCClass.__init__)
