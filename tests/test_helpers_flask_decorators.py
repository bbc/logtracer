from unittest.mock import MagicMock, patch, call

from logtracer.helpers.flask.decorators import trace_and_log_route, trace_and_log_exception, log_exception


@patch('logtracer.helpers.flask.decorators.start_traced_span')
@patch('logtracer.helpers.flask.decorators.end_traced_span')
@patch('logtracer.helpers.flask.decorators.get_logger')
@patch('logtracer.helpers.flask.decorators.request')
def test_trace_and_log_route(m_request, m_get_logger, m_end_traced_span, m_start_traced_span):
    m_route, m_response, m_logger = MagicMock(), MagicMock(), MagicMock()
    m_get_logger.return_value = m_logger
    m_response.status = 'test_response_status'
    m_route.return_value = m_response, 'test_status_number'
    m_request.headers = 'test_headers'
    m_request.path = 'test_path'
    m_request.method = 'test_method'
    m_request.url = 'test_url'

    wrapper = trace_and_log_route(m_route)
    wrapper('arg', kwarg='kwarg')

    m_start_traced_span.assert_called_with('test_headers', 'test_path')
    expected_logs = [call('test_method - test_url'), call('test_response_status - test_url')]
    assert m_logger.info.call_args_list == expected_logs
    assert m_route.called_with('arg', kwarg='kwarg')
    assert m_end_traced_span.called


@patch('logtracer.helpers.flask.decorators.end_traced_span')
@patch('logtracer.helpers.flask.decorators.get_logger')
@patch('logtracer.helpers.flask.decorators.request')
def test_trace_and_log_exception(m_request, m_get_logger, m_end_traced_span):
    m_exception_handler, m_exception, m_response, m_logger = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    m_get_logger.return_value = m_logger
    m_response.status = 'test_response_status'
    m_exception_handler.return_value = m_response
    m_request.url = 'test_url'

    wrapper = trace_and_log_exception(m_exception_handler)
    response = wrapper(m_exception)

    m_exception_handler.assert_called_with(m_exception)
    m_logger.exception.assert_called_with(m_exception)
    m_logger.error.assert_called_with('test_response_status - test_url')
    assert m_end_traced_span.called
    assert response == m_response


@patch('logtracer.helpers.flask.decorators.get_logger')
def test_log_exception(m_get_logger):
    m_exception_handler, m_exception, m_response, m_logger = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    m_get_logger.return_value = m_logger
    m_exception_handler.return_value = m_response

    wrapper = log_exception(m_exception_handler)
    response = wrapper(m_exception)

    m_exception_handler.assert_called_with(m_exception)
    m_logger.exception.assert_called_with(m_exception)
    assert response == m_response
