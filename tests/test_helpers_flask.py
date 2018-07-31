# do these then done
# separate out examples and do double grpc call
# remove mixed example
# set up with drone
from unittest.mock import patch, MagicMock

from pytest import mark

from logtracer.helpers.flask.callbacks import start_span_and_log_request_before, log_response_after, \
    close_span_on_teardown, _is_path_excluded


@patch('logtracer.helpers.flask.callbacks.start_traced_span')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
def test_start_span_and_log_request_before(m_path_exclude, m_request, m_get_logger, m_start_traced_span):
    m_path_exclude.return_value = False
    m_request.headers = 'test_headers'
    m_request.method = 'test_method'
    m_request.path = 'test_path'
    m_request.url = 'test_url'
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger

    execute_before_request = start_span_and_log_request_before(['excluded_routes'], ['excluded_partial_routes'])
    execute_before_request()

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    m_start_traced_span.assert_called_with('test_headers', 'test_path')
    m_logger.info.assert_called_with('test_method - test_url')


@patch('logtracer.helpers.flask.callbacks.start_traced_span')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
def test_start_span_and_log_request_before_excluded_route(m_path_exclude, m_get_logger, m_start_traced_span):
    m_path_exclude.return_value = True

    execute_before_request = start_span_and_log_request_before(['excluded_routes'], ['excluded_partial_routes'])
    execute_before_request()

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    assert not m_start_traced_span.called
    assert not m_get_logger.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
@mark.parametrize('success_status_code', [200, 201, 300, 301])
def test_log_response_after_success(m_request, m_get_logger, m_path_exclude, success_status_code):
    m_path_exclude.return_value = False
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = success_status_code
    m_response.status = 'test_status'

    execute_after_request = log_response_after(['excluded_routes'], ['excluded_partial_routes'])
    execute_after_request(m_response)

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    m_logger.info.assert_called_with('test_status - test_url')
    assert not m_logger.error.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
@mark.parametrize('error_status_code', [400, 401, 500, 501])
def test_log_response_after_error(m_request, m_get_logger, m_path_exclude, error_status_code):
    m_path_exclude.return_value = False
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = error_status_code
    m_response.status = 'test_status'

    execute_after_request = log_response_after(['excluded_routes'], ['excluded_partial_routes'])
    execute_after_request(m_response)

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    m_logger.error.assert_called_with('test_status - test_url')
    assert not m_logger.info.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@mark.parametrize('error_status_code', [400, 401, 500, 501])
def test_log_response_after_excluded_route(m_get_logger, m_path_exclude, error_status_code):
    m_path_exclude.return_value = True

    execute_after_request = log_response_after(['excluded_routes'], ['excluded_partial_routes'])
    execute_after_request(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    assert not m_get_logger.info.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.end_traced_span')
def test_close_span_on_teardown(m_end_traced_span, m_path_exclude):
    m_path_exclude.return_value = False

    execute_on_teardown = close_span_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    assert m_end_traced_span.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.end_traced_span')
def test_close_span_on_teardown_excluded_route(m_end_traced_span, m_path_exclude):
    m_path_exclude.return_value = True

    execute_on_teardown = close_span_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    assert not m_end_traced_span.called


@patch('logtracer.helpers.flask.callbacks.request')
def test_is_path_excluded_not_excluded(m_request):
    m_request.path = '/not_excluded'
    assert not _is_path_excluded(None, None)

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(['/excluded'], None)

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(None, ['/excluded'])

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(['/excluded'], ['/also_excluded'])


@patch('logtracer.helpers.flask.callbacks.request')
def test_is_path_excluded_excluded(m_request):
    m_request.path = '/excluded'
    assert _is_path_excluded(['/excluded'], None)

    m_request.path = '/excluded'
    assert _is_path_excluded(None, ['/exclu'])

    m_request.path = '/also_excluded_route'
    assert _is_path_excluded(['/excluded'], ['/also_excluded'])

    m_request.path = '/excluded'
    assert _is_path_excluded(['/excluded'], ['/also_excluded'])
