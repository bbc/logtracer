import re

from pytest import fixture

import logtrace._b3


@fixture
def b3():
    yield logtrace._b3
    b3.DEBUG = False
    logtrace._b3._end_subspan()


def test_should_generate_root_span_ids(b3):
    # Given
    # No B3 headers - this is the root span
    b3.start_span({})

    # When
    # We get the B3 values
    values = b3.values()

    # Then
    # Both trace ID and span ID should have been genenated
    assert values[b3.B3_TRACE_ID]
    assert values[b3.B3_SPAN_ID]
    # The IDs should be 16 characters of hex
    assert re.match("[a-fA-F0-9]{16}", values[b3.B3_TRACE_ID])
    assert re.match("[a-fA-F0-9]{16}", values[b3.B3_SPAN_ID])


def test_should_maintain_trace_id(b3):
    # Given
    # A trace ID in the B3 headers
    trace_id = "Barbapapa"
    b3.start_span({b3.B3_TRACE_ID: trace_id})

    # When
    # We get b3 values and update onward request headers
    values = b3.values()
    headers = b3._start_subspan()

    # Then
    # The incoming trace ID should be maintained
    assert trace_id == values[b3.B3_TRACE_ID]
    assert trace_id == headers[b3.B3_TRACE_ID]


def test_should_propagate_span_id_as_parent(b3):
    # Given
    # A trace ID in the B3 headers
    span_id = "Barbabright"
    b3.start_span({b3.B3_SPAN_ID: span_id})

    # When
    # We update onward request headers
    headers = b3._start_subspan()

    # Then
    # The incoming trace ID should be propagated
    assert span_id == headers[b3.B3_PARENT_SPAN_ID]


def test_should_propagate_with_new_span_id(b3):
    # Given
    # A trace ID in the B3 headers
    span_id = "Barbazoo"
    b3.start_span({b3.B3_SPAN_ID: span_id})

    # When
    # We update onward request headers
    headers = b3._start_subspan()

    # Then
    # The incoming trace ID should be propagated
    assert span_id != headers[b3.B3_SPAN_ID]
    # The ID should be 16 characters of hex
    assert re.match("[a-fA-F0-9]{16}", headers[b3.B3_SPAN_ID])


def test_should_not_set_sampled(b3):
    # Given
    # Sampled is not set in the request headers
    b3.start_span({})

    # When
    # We get b3 values and update onward request headers
    values = b3.values()
    headers = b3._start_subspan()

    # Then
    # Sampled should not be set and should
    # remain absent from onward request headers
    assert not values[b3.B3_SAMPLED]
    assert not b3.B3_SAMPLED in headers


def test_should_maintain_sampled(b3):
    # Given
    # Sampled is not set in the request headers
    sampled = '0'
    b3.start_span({b3.B3_SAMPLED: sampled})

    # When
    # We get b3 values and update onward request headers
    values = b3.values()
    headers = b3._start_subspan()

    # Then
    # The Sampled value should be maintained
    assert sampled == values[b3.B3_SAMPLED]
    assert sampled == headers[b3.B3_SAMPLED]


def test_should_maintain_flags_for_debug(b3):
    # Given
    # Flags is set in the B3 headers
    flags = '1'
    b3.start_span({b3.B3_FLAGS: flags})

    # When
    # We get b3 values and update onward request headers
    values = b3.values()
    headers = b3._start_subspan()

    # Then
    # Flags should be set to 1 to indicate debug
    assert flags == values[b3.B3_FLAGS]
    assert flags == headers[b3.B3_FLAGS]


def test_should_set_flags_for_debug(b3):
    # Given
    # We have set debug on
    b3.DEBUG = True
    b3.start_span({})

    # When
    # We get b3 values and update onward request headers
    values = b3.values()
    headers = b3._start_subspan()

    # Then
    # Flags should be set to 1 to indicate debug
    assert "1" == values[b3.B3_FLAGS]
    assert "1" == headers[b3.B3_FLAGS]


def test_should_update_span_info_on_subspan_start(b3):
    # Given
    # We have a full set of span values
    b3.start_span({b3.B3_SAMPLED: "1", b3.B3_FLAGS: "1"})

    # When
    # We start a subspan
    span = b3.values()
    b3._start_subspan()

    # Then
    # Values should now reflect the sub-span
    subspan = b3.values()
    assert span[b3.B3_TRACE_ID] == subspan[b3.B3_TRACE_ID]
    assert span[b3.B3_SPAN_ID] == subspan[b3.B3_PARENT_SPAN_ID]
    assert span[b3.B3_SPAN_ID] != subspan[b3.B3_SPAN_ID]
    assert span[b3.B3_SAMPLED] == subspan[b3.B3_SAMPLED]
    assert span[b3.B3_FLAGS] == subspan[b3.B3_FLAGS]


def test_should_revert_span_info_on_subspan_end(b3):
    # Given
    # We have a full set of span values and a subspan
    b3.start_span({b3.B3_SAMPLED: "1", b3.B3_FLAGS: "1"})
    span = b3.values()
    b3._start_subspan()

    # When
    # We end the subspan
    b3._end_subspan()

    # Then
    # Values should now reflect the sub-span
    reverted = b3.values()
    assert span[b3.B3_TRACE_ID] == reverted[b3.B3_TRACE_ID]
    assert span[b3.B3_PARENT_SPAN_ID] == reverted[b3.B3_PARENT_SPAN_ID]
    assert span[b3.B3_SPAN_ID] == reverted[b3.B3_SPAN_ID]
    assert span[b3.B3_SAMPLED] == reverted[b3.B3_SAMPLED]
    assert span[b3.B3_FLAGS] == reverted[b3.B3_FLAGS]


def test_should_update_headers_if_passed(b3):
    # Given
    # We have some existing headers
    headers_original = {'Barbabeau': 'Barbalala'}

    # When
    # We update the headers
    headers_updated = b3._start_subspan(headers_original)

    # Then
    # headers should still contain the original header values
    # https://stackoverflow.com/questions/9323749/python-check-if-one-dictionary-is-a-subset-of-another-larger-dictionary
    assert set(headers_updated).issuperset(set(headers_original))
