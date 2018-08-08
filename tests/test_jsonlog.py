import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

from logtracer import _global_vars
from logtracer.tracing import B3_TRACE_ID, B3_PARENT_SPAN_ID, B3_SPAN_ID
from logtracer.jsonlog import StackdriverJsonFormatter, LocalJsonFormatter, configure_json_logging, get_logger


class TestException(Exception):
    pass


@patch('logtracer.jsonlog._b3.values', MagicMock(return_value={}))
def test_StackdriverJsonFormatter_add_fields_no_trace():
    json_formatter = StackdriverJsonFormatter()

    mock_record = MagicMock()
    mock_record.exc_info = None
    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message"
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    expected_mock_log_record = {
        'logging.googleapis.com/sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'message': 'test_name - test_message',
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651)
    }

    assert mock_log_record == expected_mock_log_record


@patch('logtracer.jsonlog._b3.values')
def test_StackdriverJsonFormatter_add_fields_with_trace(m_b3_values):
    json_formatter = StackdriverJsonFormatter()

    m_b3_values.return_value = {
        B3_SPAN_ID: "test_span_id",
        B3_PARENT_SPAN_ID: "test_parent_span_id",
        B3_TRACE_ID: "test_trace_id"
    }
    _global_vars.gcp_project_name = 'test_project_name'
    mock_record = MagicMock()
    mock_record.exc_info = None
    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message",
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    expected_mock_log_record = {
        'logging.googleapis.com/sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'message': 'test_name - test_message',
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651),
        'logging.googleapis.com/spanId': 'test_span_id',
        'logging.googleapis.com/trace': 'projects/test_project_name/traces/test_trace_id',

    }

    assert mock_log_record == expected_mock_log_record


@patch('logtracer.jsonlog._b3.values', MagicMock(return_value={}))
def test_StackdriverJsonFormatter_add_fields_with_exc_info():
    json_formatter = StackdriverJsonFormatter()
    mock_record = MagicMock()

    try:
        raise TestException('This is a test!')
    except TestException:
        exception_class, exception, tb = sys.exc_info()

    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message",
        'exc_info': (exception_class, exception, tb)
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    exc_message = mock_log_record.pop('message')
    assert 'Exception: TestException(This is a test!)' in exc_message

    expected_mock_log_record = {
        'logging.googleapis.com/sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651),
    }

    assert mock_log_record == expected_mock_log_record


@patch('logtracer.jsonlog._b3.values', MagicMock(return_value={}))
def test_LocalJsonFormatter_add_fields_no_trace():
    json_formatter = LocalJsonFormatter()

    mock_record = MagicMock()
    mock_record.exc_info = None
    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message"
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    expected_mock_log_record = {
        'sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'message': 'test_name - test_message',
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651)
    }

    assert mock_log_record == expected_mock_log_record


@patch('logtracer.jsonlog._b3.values')
def test_LocalJsonFormatter_add_fields_with_trace(m_b3_values):
    json_formatter = LocalJsonFormatter()

    m_b3_values.return_value = {
        B3_SPAN_ID: "test_span_id",
        B3_PARENT_SPAN_ID: "test_parent_span_id",
        B3_TRACE_ID: "test_trace_id"
    }
    _global_vars.gcp_project_name = 'test_project_name'
    mock_record = MagicMock()
    mock_record.exc_info = None
    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message",
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    expected_mock_log_record = {
        'sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'message': 'test_name - test_message',
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651),
        'spanId': 'test_span_id',
        'traceId': 'test_trace_id',

    }

    assert mock_log_record == expected_mock_log_record


@patch('logtracer.jsonlog._b3.values', MagicMock(return_value={}))
def test_LocalJsonFormatter_add_fields_with_exc_info():
    json_formatter = LocalJsonFormatter()
    mock_record = MagicMock()

    try:
        raise TestException('This is a test!')
    except TestException:
        exception_class, exception, tb = sys.exc_info()

    mock_record_dict = {
        'levelname': 'INFO',
        'created': 1532963448.341651,
        'pathname': "test_pathname",
        'lineno': "test_lineno",
        'funcName': 'test_function',
        'name': 'test_name',
        'message': "test_message",
        'exc_info': (exception_class, exception, tb)
    }
    for attr, val in mock_record_dict.items():
        setattr(mock_record, attr, val)

    mock_log_record = {}

    json_formatter.add_fields(mock_log_record, mock_record, {})

    exc_message = mock_log_record.pop('message')
    assert 'Exception: TestException(This is a test!)' in exc_message

    expected_mock_log_record = {
        'sourceLocation':
            {
                'file': 'test_pathname',
                'function': 'test_function',
                'line': 'test_lineno'
            },
        'severity': 'INFO',
        'time': datetime(2018, 7, 30, 16, 10, 48, 341651),
    }

    assert mock_log_record == expected_mock_log_record


def test_configure_json_logging_local():
    configure_json_logging('test_project_name', 'test_service_name', 'local')

    assert _global_vars.gcp_project_name == 'test_project_name'
    assert _global_vars.service_name == 'test_service_name'

    logger = get_logger()
    assert logger.name == 'test_service_name'
    assert isinstance(logger.root.handlers[0].formatter, LocalJsonFormatter)


def test_configure_json_logging_stackdriver():
    configure_json_logging('test_project_name', 'test_service_name', 'stackdriver')

    assert _global_vars.gcp_project_name == 'test_project_name'
    assert _global_vars.service_name == 'test_service_name'

    logger = get_logger()
    assert logger.name == 'test_service_name'
    assert isinstance(logger.root.handlers[0].formatter, StackdriverJsonFormatter)
