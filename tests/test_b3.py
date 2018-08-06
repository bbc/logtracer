import re
from unittest.mock import patch

import pytest
from pytest import fixture

from logtracer import _b3 as b3
from logtracer._b3 import end_span, SpanError, generate_new_subspan_values, _generate_identifier


@fixture
def b3_mem():
    class MockB3Mem:
        pass

    mock_b3_mem = MockB3Mem()
    with patch('logtracer._b3.b3', mock_b3_mem):
        yield mock_b3_mem


def test_values_default():
    default = b3.values()

    expected = {
        b3.B3_TRACE_ID: None,
        b3.B3_PARENT_SPAN_ID: None,
        b3.B3_SPAN_ID: None,
        b3.B3_SAMPLED: None,
        b3.B3_FLAGS: None
    }

    assert default == expected


def test_values(b3_mem):
    b3_mem.span = 'existing_span'
    span = b3.values()
    assert span == 'existing_span'


@patch('logtracer._b3._generate_identifier', lambda x: f'generated uuid {x} chars long')
def test_start_span_no_headers(b3_mem):
    b3.start_span({})

    expected_span = {
        b3.B3_TRACE_ID: "generated uuid 32 chars long",
        b3.B3_PARENT_SPAN_ID: None,
        b3.B3_SPAN_ID: "generated uuid 16 chars long",
        b3.B3_SAMPLED: None,
        b3.B3_FLAGS: None
    }

    assert b3_mem.span == expected_span


@patch('logtracer._b3._generate_identifier', lambda x: f'generated uuid {x} chars long')
def test_start_span_with_headers(b3_mem):
    incoming_headers = {
        b3.B3_TRACE_ID: "test_trace_id",
        b3.B3_PARENT_SPAN_ID: "test_parent_span_id",
        b3.B3_SPAN_ID: "test_span_id",
        b3.B3_SAMPLED: "test_sampled",
        b3.B3_FLAGS: "test_flags"
    }

    b3.start_span(incoming_headers)

    expected_span = {
        b3.B3_TRACE_ID: "test_trace_id",
        b3.B3_PARENT_SPAN_ID: "test_parent_span_id",
        b3.B3_SPAN_ID: "test_span_id",
        b3.B3_SAMPLED: "test_sampled",
        b3.B3_FLAGS: "test_flags"
    }

    assert b3_mem.span == expected_span


def test_end_span(b3_mem):
    b3_mem.span = 'span'
    end_span()
    assert not hasattr(b3_mem, 'span')


def test_end_span_doesnt_exist():
    with pytest.raises(SpanError):
        end_span()


@patch('logtracer._b3.values')
@patch('logtracer._b3._generate_identifier', lambda x: f'generated uuid {x} chars long')
def test_generate_new_subspan_values(m_values, b3_mem):
    b3_mem.span = ''
    m_values.return_value = {
        b3.B3_TRACE_ID: "test_trace_id",
        b3.B3_PARENT_SPAN_ID: "test_parent_span_id",
        b3.B3_SPAN_ID: "test_span_id",
        b3.B3_SAMPLED: None,
        b3.B3_FLAGS: None
    }
    new_vals = generate_new_subspan_values()

    expected_new_vals = {
        b3.B3_PARENT_SPAN_ID: 'test_span_id',
        b3.B3_SPAN_ID: 'generated uuid 16 chars long',
        b3.B3_TRACE_ID: 'test_trace_id'
    }

    assert new_vals == expected_new_vals


def test_generate_new_subspan_values_no_span(b3_mem):
    with pytest.raises(SpanError):
        generate_new_subspan_values()


@pytest.mark.parametrize('id_len', [2, 4, 8, 16, 32, 64, 128, 256, 512])
def test_generate_identifier(id_len):
    gen_id = _generate_identifier(id_len)
    assert re.match("[a-fA-F0-9]{%d}" % id_len, gen_id)


@pytest.mark.parametrize('id_len', [0, 3, 15, -5])
def test_generate_identifier_fail(id_len):
    with pytest.raises(ValueError):
        _generate_identifier(id_len)
