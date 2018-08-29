from unittest.mock import MagicMock

import pytest

from logtracer.helpers.grpc.redact import _rsetattr, _rgetattr, redact_request


def test_rsetattr():
    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr', 'test_val')
    assert m_obj.test_attr == 'test_val'

    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr1.test_attr2', 'test_val')
    assert m_obj.test_attr1.test_attr2 == 'test_val'

    m_obj = MagicMock()
    _rsetattr(m_obj, 'test_attr1.test_attr2.test_attr3', 'test_val')
    assert m_obj.test_attr1.test_attr2.test_attr3 == 'test_val'


def test_rgetattr():
    m_obj = object()
    with pytest.raises(AttributeError):
        _rgetattr(m_obj, 'test_attr')

    m_obj = MagicMock()
    m_obj.test_attr1 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1') == 'test_val'

    m_obj = MagicMock()
    m_obj.test_attr1.test_attr2 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1.test_attr2') == 'test_val'

    m_obj = MagicMock()
    m_obj.test_attr1.test_attr2.test_attr3 = 'test_val'
    assert _rgetattr(m_obj, 'test_attr1.test_attr2.test_attr3') == 'test_val'


def test_redact_request():
    m_request = MagicMock()
    m_request.test_sensitive_field = 'sensitive_val'
    m_request.test_unsensitive_field = 'unsensitive_val'
    m_request.test_nested.test_sensitive_field = 'sensitive_val'
    m_request.test_nested.test_field = 'unsensitive_val'

    redacted = redact_request(m_request, ['test_sensitive_field', 'test_nested.test_sensitive_field'])

    assert m_request.test_sensitive_field == 'sensitive_val'
    assert m_request.test_unsensitive_field == 'unsensitive_val'
    assert m_request.test_nested.test_sensitive_field == 'sensitive_val'
    assert m_request.test_nested.test_field == 'unsensitive_val'

    assert redacted.test_sensitive_field == 'REDACTED'
    assert redacted.test_unsensitive_field == 'unsensitive_val'
    assert redacted.test_nested.test_sensitive_field == 'REDACTED'
    assert redacted.test_nested.test_field == 'unsensitive_val'
