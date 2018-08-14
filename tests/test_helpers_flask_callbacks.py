from unittest.mock import patch, MagicMock

import pytest
from pytest import mark

from logtracer.helpers.flask.tracer import start_span_and_log_request_before, log_response_after, \
    close_span_and_post_on_teardown
from logtracer.helpers.flask.path_exclusion import _is_path_excluded


@patch('logtracer.helpers.flask.callbacks.start_traced_span')
@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
def test_start_span_and_log_request_before(m_request, m_get_logger, m_start_traced_span):
    m_request.headers = 'test_headers'
    m_request.method = 'test_method'
    m_request.path = 'test_path'
    m_request.url = 'test_url'
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger

    execute_before_request = start_span_and_log_request_before()
    execute_before_request()

    m_start_traced_span.assert_called_with('test_headers', 'test_path')
    m_logger.info.assert_called_with('test_method - test_url')


@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
@mark.parametrize('success_status_code', [200, 201, 300, 301])
def test_log_response_after_success(m_request, m_get_logger, success_status_code):
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = success_status_code
    m_response.status = 'test_status'

    execute_after_request = log_response_after()
    execute_after_request(m_response)

    m_logger.info.assert_called_with('test_status - test_url')
    assert not m_logger.error.called


@patch('logtracer.helpers.flask.callbacks.get_logger')
@patch('logtracer.helpers.flask.callbacks.request')
@mark.parametrize('error_status_code', [400, 401, 500, 501])
def test_log_response_after_error(m_request, m_get_logger, error_status_code):
    m_logger = MagicMock()
    m_get_logger.return_value = m_logger
    m_request.url = 'test_url'
    m_response = MagicMock()
    m_response.status_code = error_status_code
    m_response.status = 'test_status'

    execute_after_request = log_response_after()
    execute_after_request(m_response)

    m_logger.error.assert_called_with('test_status - test_url')
    assert not m_logger.info.called


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.end_traced_span')
def test_close_span_on_teardown(m_end_traced_span, m_path_exclude):
    m_path_exclude.return_value = False

    execute_on_teardown = close_span_and_post_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    m_end_traced_span.assert_called_with(False)


@patch('logtracer.helpers.flask.callbacks._is_path_excluded')
@patch('logtracer.helpers.flask.callbacks.end_traced_span')
def test_close_span_on_teardown(m_end_traced_span, m_path_exclude):
    m_path_exclude.return_value = False

    execute_on_teardown = close_span_and_post_on_teardown(['excluded_routes'], ['excluded_partial_routes'])
    execute_on_teardown(MagicMock())

    m_path_exclude.assert_called_with(['excluded_routes'], ['excluded_partial_routes'])
    m_end_traced_span.assert_called_with(True)


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


def test_is_path_excluded_error():
    with pytest.raises(ValueError):
        assert _is_path_excluded('test_string', None)

    with pytest.raises(ValueError):
        assert _is_path_excluded(None, 'test_string')

    with pytest.raises(ValueError):
        assert _is_path_excluded('test_string', 'test_string')
