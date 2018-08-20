from logging import exception
from unittest.mock import MagicMock, patch, call

import pytest

from logtracer.helpers.grpc.tracer import GRPCTracer, _IncomingInterceptor, _OutgoingInterceptor


def test_GRPCTracer_init():
    m_logger_factory = MagicMock()

    grpc_tracer = GRPCTracer(m_logger_factory, redacted_fields='test_redacted_fields')
    assert isinstance(grpc_tracer.server_interceptor(), _IncomingInterceptor)
    assert isinstance(grpc_tracer.client_interceptor(), _OutgoingInterceptor)
    assert grpc_tracer.redacted_fields == 'test_redacted_fields'


@patch('logtracer.helpers.grpc.tracer._wrap_rpc_behavior', MagicMock(side_effect=lambda handler, fn: fn))
@patch('logtracer.helpers.grpc.tracer.redact_request', return_value='test_redacted_request')
@patch('logtracer.helpers.grpc.tracer._grpc_status_from_context', return_value='.test_grpc_status')
def test_IncomingInterceptor(m_grpc_status, m_redact):
    m_tracer = MagicMock()
    interceptor = _IncomingInterceptor(m_tracer)
    interceptor._retrieve_span_values_from_incoming_call = MagicMock(return_value='test_b3_values')
    interceptor._tracer = MagicMock()
    interceptor._tracer.redacted_fields = 'test_fields_to_redact'
    m_continuation, m_handler_call_details = MagicMock(), MagicMock()
    m_handler_call_details.method = 'test_method'
    m_behaviour = MagicMock()
    m_request, m_servicer_context = MagicMock(), MagicMock()
    m_request.ListFields.return_value = True

    tracing_wrapper = interceptor.intercept_service(m_continuation, m_handler_call_details)
    new_behaviour_func = tracing_wrapper(m_behaviour)
    new_behaviour = new_behaviour_func(m_request, m_servicer_context)

    interceptor._tracer.start_traced_span.assert_called_with('test_b3_values', m_handler_call_details.method)
    m_redact.assert_called_with(m_request, 'test_fields_to_redact')
    m_grpc_status.assert_called_with(m_servicer_context)
    m_behaviour.assert_called_with(m_request, m_servicer_context)
    expected_logs = [
        call('test_method - received gRPC call \nrequest: test_redacted_request'),
        call('test_method.test_grpc_status - returning gRPC call')
    ]
    assert interceptor._tracer.logger.info.call_args_list == expected_logs
    interceptor._tracer.end_traced_span.assert_called_with(exclude_from_posting=False)


@patch('logtracer.helpers.grpc.tracer._wrap_rpc_behavior', MagicMock(side_effect=lambda handler, fn: fn))
@patch('logtracer.helpers.grpc.tracer.redact_request', return_value='test_redacted_request')
@patch('logtracer.helpers.grpc.tracer._grpc_status_from_context', return_value='.test_grpc_status')
def test_IncomingInterceptor_exception(m_grpc_status, m_redact):
    class TestException(Exception):
        pass

    m_tracer = MagicMock()
    interceptor = _IncomingInterceptor(m_tracer)
    interceptor._retrieve_span_values_from_incoming_call = MagicMock(return_value='test_b3_values')
    interceptor._tracer = MagicMock()
    interceptor._tracer.redacted_fields = 'test_fields_to_redact'
    m_continuation, m_handler_call_details = MagicMock(), MagicMock()
    m_handler_call_details.method = 'test_method'
    m_exception = TestException('test exception')
    m_behaviour = MagicMock(side_effect=m_exception)
    m_request, m_servicer_context = MagicMock(), MagicMock()
    m_request.ListFields.return_value = True

    tracing_wrapper = interceptor.intercept_service(m_continuation, m_handler_call_details)
    new_behaviour_func = tracing_wrapper(m_behaviour)
    with pytest.raises(TestException):
        new_behaviour = new_behaviour_func(m_request, m_servicer_context)

    interceptor._tracer.start_traced_span.assert_called_with('test_b3_values', m_handler_call_details.method)
    m_redact.assert_called_with(m_request, 'test_fields_to_redact')
    m_grpc_status.assert_called_with(m_servicer_context)
    m_behaviour.assert_called_with(m_request, m_servicer_context)
    interceptor._tracer.logger.info.assert_called_with(
        'test_method - received gRPC call \nrequest: test_redacted_request'
    )
    interceptor._tracer.logger.error.assert_called_with(
        'test_method - TestException.test_grpc_status'
    )
    interceptor._tracer.logger.exception.assert_called_with(m_exception)
    interceptor._tracer.end_traced_span.assert_called_with(exclude_from_posting=False)
