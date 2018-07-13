from unittest.mock import patch

from gcptracelogging.tracing import _truncate_str, g, start_span, TracedSubSpan


def test_truncate_str():
    shortstr = 'short'
    trunc_obj = _truncate_str(shortstr, limit=10)
    assert trunc_obj == {'value': 'short', 'truncated_byte_count': 0}

    longstr = 'kindoflongstring'
    trunc_obj = _truncate_str(longstr, limit=10)
    assert trunc_obj == {'value': 'kindoflong', 'truncated_byte_count': 6}


@patch('gcptracelogging.tracing.b3.SubSpan')
@patch('gcptracelogging.tracing.b3.start_span')
def test_g_child_span_count(startspan, subspan):
    start_span({}, '', '', '')
    assert g.child_span_count == 0

    with TracedSubSpan() as _:
        pass
    assert g.child_span_count == 1

    with TracedSubSpan() as _:
        pass
    assert g.child_span_count == 2
