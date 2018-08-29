from unittest.mock import MagicMock, patch

from logtracer.helpers.mixed.tracing import MixedTracer


@patch('logtracer.helpers.mixed.tracing.GRPCTracer.__init__')
@patch('logtracer.helpers.mixed.tracing.FlaskTracer.__init__')
def test_MixedTracer(m_flask_tracer_init, m_grpc_tracer_init):
    m_logger_factory = MagicMock()
    MixedTracer(m_logger_factory, post_spans_to_stackdriver_api=False)

    m_grpc_tracer_init.assert_called_with(m_logger_factory, False)
    assert not m_flask_tracer_init.called
