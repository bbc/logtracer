from unittest.mock import MagicMock, patch

from logtracer.helpers.flask.decorators import log_exception


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
