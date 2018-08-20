import json
from unittest.mock import MagicMock, patch, call

import pytest
from grpc._cython.cygrpc import _Metadatum

from logtracer.helpers.grpc.tracer import GRPCTracer, _IncomingInterceptor, _OutgoingInterceptor, B3_VALUES_KEY


def test_GRPCTracer_init():
    m_logger_factory = MagicMock()

    grpc_tracer = GRPCTracer(m_logger_factory, redacted_fields='test_redacted_fields')
    assert isinstance(grpc_tracer.server_interceptor(), _IncomingInterceptor)
    assert isinstance(grpc_tracer.client_interceptor(), _OutgoingInterceptor)
    assert grpc_tracer.redacted_fields == 'test_redacted_fields'


def test_IncomingInterceptor_init():
    m_tracer = MagicMock()
    assert _IncomingInterceptor(m_tracer)._tracer == m_tracer


@patch('logtracer.helpers.grpc.tracer._wrap_rpc_behavior', MagicMock(side_effect=lambda handler, fn: fn))
@patch('logtracer.helpers.grpc.tracer.redact_request', return_value='test_redacted_request')
@patch('logtracer.helpers.grpc.tracer._grpc_status_from_context', return_value='.test_grpc_status')
def test_IncomingInterceptor_intercept_service(m_grpc_status, m_redact):
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
def test_IncomingInterceptor_intercept_service_exception(m_grpc_status, m_redact):
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


def test_IncomingInterceptor_retrieve_span_values_from_incoming_call():
    m_handler_call_details = MagicMock()
    m_handler_call_details.invocation_metadata = [
        _Metadatum(key=B3_VALUES_KEY, value=json.dumps({'test_b3_values': 'values'})),
        _Metadatum(key='other_key', value='test_other_value')
    ]

    values = _IncomingInterceptor._retrieve_span_values_from_incoming_call(m_handler_call_details)

    assert values == {'test_b3_values': 'values'}


def test_IncomingInterceptor_retrieve_span_values_from_incoming_call_no_values():
    m_handler_call_details = MagicMock()
    m_handler_call_details.invocation_metadata = [
        _Metadatum(key='other_key', value='test_other_value')
    ]

    values = _IncomingInterceptor._retrieve_span_values_from_incoming_call(m_handler_call_details)

    assert values == {}


def test_OutgoingInterceptor_init():
    m_tracer = MagicMock()
    assert _OutgoingInterceptor(m_tracer)._tracer == m_tracer


def test_OutgoingInterceptor_intercept_unary_unary():
    m_tracer = MagicMock()
    interceptor = _OutgoingInterceptor(m_tracer)
    interceptor._generate_metadata_with_b3_values = MagicMock(return_value='test_metadata_with_b3_values')
    m_continuation, m_client_call_details, m_request = MagicMock(), MagicMock(), MagicMock()
    m_response_future = MagicMock()
    m_continuation.return_value = m_response_future
    m_client_call_details.method = 'test_method'
    m_client_call_details.timeout = 'test_timeout'
    m_client_call_details.credentials = 'test_credentials'

    response_future = interceptor.intercept_unary_unary(m_continuation, m_client_call_details, m_request)

    expected_logs = [
        call('test_method - outbound gRPC call'),
        call('Response received from test_method')
    ]
    assert interceptor._tracer.logger.info.call_args_list == expected_logs
    modified_client_call_details = m_continuation.call_args[0][0]
    assert modified_client_call_details.method == 'test_method'
    assert modified_client_call_details.timeout == 'test_timeout'
    assert modified_client_call_details.credentials == 'test_credentials'
    assert modified_client_call_details.metadata == 'test_metadata_with_b3_values'
    assert m_response_future.result.called
    assert response_future == m_response_future
