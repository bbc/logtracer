from unittest.mock import MagicMock

import pytest

from logtracer.exceptions import SpanNotStartedError
from logtracer.tracing import SpanContext, SubSpanContext


def test_spancontext():
    m_tracer = MagicMock()
    with SpanContext(m_tracer, {'test': 'headers'}, 'test_span_name', exclude_from_posting='test_exclude_bool'):
        m_tracer.start_traced_span.assert_called_with({'test': 'headers'}, 'test_span_name')
        assert not m_tracer.end_traced_span.called
    m_tracer.end_traced_span.assert_called_with('test_exclude_bool')


def test_subspancontext_no_span():
    m_tracer = MagicMock()
    m_tracer.start_traced_subspan.side_effect = SpanNotStartedError
    with pytest.raises(SpanNotStartedError):
        with SubSpanContext(m_tracer, 'test_span_name', 'test_exclude_bool'):
            pass