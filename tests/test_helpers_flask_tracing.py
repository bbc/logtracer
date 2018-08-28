from unittest.mock import MagicMock, patch

from pytest import mark

from logtracer.helpers.flask.tracing import FlaskTracer


@patch('logtracer.helpers.flask.tracing.request')
def test_FlaskTracer_start_span_and_log_request_before(m_request):
    m_request.headers = 'test_headers'
    m_request.method = 'test_method'
    m_request.path = 'test_path'
    m_request.url = 'test_url'
    m_logger_factory = MagicMock()
    flask_tracer = FlaskTracer(m_logger_factory)
    flask_tracer.start_traced_span = MagicMock()

    execute_before_request = flask_tracer.start_span_and_log_request_before()
    execute_before_request()

    flask_tracer.start_traced_span.assert_called_with('test_headers', 'test_path')
    flask_tracer.logger.info.assert_called_with('test_method - test_url')


@patch('logtracer.helpers.flask.tracing.request')
@mark.parametrize('success_status_code', [200, 201, 300, 301])
def test_FlaskTracer_start_span_and_log_request_before(m_request, success_status_code):
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = success_status_code
    m_response.status = 'test_status'
    m_logger_factory = MagicMock()
    flask_tracer = FlaskTracer(m_logger_factory)

    execute_after_request = flask_tracer.log_response_after()
    execute_after_request(m_response)

    flask_tracer.logger.info.assert_called_with('test_status - test_url')
    assert not flask_tracer.logger.error.called


@patch('logtracer.helpers.flask.tracing.request')
@mark.parametrize('error_status_code', [400, 401, 500, 501])
def test_FlaskTracer_log_response_after_error(m_request, error_status_code):
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = error_status_code
    m_response.status = 'test_status'
    m_logger_factory = MagicMock()
    flask_tracer = FlaskTracer(m_logger_factory)

    execute_after_request = flask_tracer.log_response_after()
    execute_after_request(m_response)

    flask_tracer.logger.error.assert_called_with('test_status - test_url')
    assert not flask_tracer.logger.info.called


@patch('logtracer.helpers.flask.tracing._is_path_excluded')
def test_FlaskTracer_end_span_on_teardown(m_path_exclude):
    m_path_exclude.return_value = False
    m_logger_factory = MagicMock()
    flask_tracer = FlaskTracer(m_logger_factory)
    flask_tracer.end_traced_span = MagicMock()

    execute_on_teardown = flask_tracer.end_span_and_post_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    flask_tracer.end_traced_span.assert_called_with(False)


@patch('logtracer.helpers.flask.tracing._is_path_excluded')
def test_FlaskTracer_end_span_on_teardown_exclude_path(m_path_exclude):
    m_path_exclude.return_value = True
    m_logger_factory = MagicMock()
    flask_tracer = FlaskTracer(m_logger_factory)
    flask_tracer.end_traced_span = MagicMock()

    execute_on_teardown = flask_tracer.end_span_and_post_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    flask_tracer.end_traced_span.assert_called_with(True)


def test_FlaskTracer_log_exception():
    m_logger_factory = MagicMock()
    m_exception_handler, m_exception, m_response, m_logger_factory.logger = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    m_exception_handler.return_value = m_response
    flask_tracer = FlaskTracer(m_logger_factory)

    wrapper = flask_tracer.log_exception(m_exception_handler)
    response = wrapper(m_exception)

    m_exception_handler.assert_called_with(m_exception)
    flask_tracer.logger.exception.assert_called_with(m_exception)
    assert response == m_response
