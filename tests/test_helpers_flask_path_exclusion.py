from unittest.mock import patch

import pytest

from logtracer.helpers.flask.path_exclusion import _is_path_excluded


@patch('logtracer.helpers.flask.path_exclusion.request')
def test_is_path_excluded_not_excluded(m_request):
    m_request.path = '/not_excluded'
    assert not _is_path_excluded(None, None)

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(['/excluded'], None)

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(None, ['/excluded'])

    m_request.path = '/not_excluded'
    assert not _is_path_excluded(['/excluded'], ['/also_excluded'])


@patch('logtracer.helpers.flask.path_exclusion.request')
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
