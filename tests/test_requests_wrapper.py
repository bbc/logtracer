from unittest.mock import MagicMock, patch


@patch('logtracer.requests_wrapper.requests.get')
@patch('logtracer.requests_wrapper.requests.post')
@patch('logtracer.tracing.SubSpanContext')
def test_unsupported_request_mapper(m_subspan, m_requests_post, m_requests_get):
    from logtracer.requests_wrapper import UnsupportedRequestsWrapper

    m_tracer = MagicMock()
    requests = UnsupportedRequestsWrapper(m_tracer)

    requests.get('http://example.com', headers={'example': 'headers'})
    m_requests_get.assert_called_with('http://example.com', headers={'example': 'headers'})
    m_subspan.assert_called_with(m_tracer, 'http://example.com')

    requests.post('http://example.com', headers={'example': 'headers'})
    m_requests_post.assert_called_with('http://example.com', headers={'example': 'headers'})
    m_subspan.assert_called_with(m_tracer, 'http://example.com')


@patch('logtracer.requests_wrapper.requests.get')
@patch('logtracer.requests_wrapper.requests.post')
def test_request_mapper(m_requests_post, m_requests_get):
    from logtracer.requests_wrapper import RequestsWrapper

    m_tracer = MagicMock()
    m_tracer.generate_new_traced_subspan_values.return_value = {'tracing': 'headers'}
    requests = RequestsWrapper(m_tracer)

    requests.get('http://example.com', headers={'example': 'headers'})
    m_requests_get.assert_called_with('http://example.com', headers={'example': 'headers', 'tracing': 'headers'})

    requests.post('http://example.com', headers={'example': 'headers'}, data={})
    m_requests_post.assert_called_with('http://example.com', data={},
                                       headers={'example': 'headers', 'tracing': 'headers'})
