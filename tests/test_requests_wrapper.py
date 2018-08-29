from unittest.mock import MagicMock, patch

from logtracer.requests_wrapper import RequestsWrapper


@patch('logtracer.requests_wrapper.requests.get')
@patch('logtracer.requests_wrapper.requests.post')
def test_request_mapper(m_requests_post, m_requests_get):
    m_tracer = MagicMock()
    m_tracer.generate_new_traced_subspan_values.return_value = {'tracing': 'headers'}
    requests = RequestsWrapper(m_tracer)

    requests.get('http://example.com', headers={'example': 'headers'})
    m_requests_get.assert_called_with('http://example.com', headers={'example': 'headers', 'tracing': 'headers'})

    requests.post('http://example.com', headers={'example': 'headers'}, data={})
    m_requests_post.assert_called_with('http://example.com', data={}, headers={'example': 'headers',  'tracing': 'headers'})
