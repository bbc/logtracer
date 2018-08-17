from datetime import datetime
from unittest.mock import patch, MagicMock

from logtracer.exceptions import SpanNotStartedError
from logtracer.jsonlog import JsonFormatter, _generate_log_record, _add_span_values, _format_message_for_exception, \
    JSONLoggerFactory

MODULE_PATH = 'logtracer.jsonlog.'


@patch(MODULE_PATH + '_format_message_for_exception')
@patch(MODULE_PATH + '_generate_log_record')
@patch(MODULE_PATH + '_add_span_values')
def test_JsonFormatter_add_fields_local(m_add_span_values, m_generate_log_record, m_format_msg_exc):
    class MockRecord:
        exc_info = 'test_exc_info'

    m_generate_log_record.return_value = {'test_generate': 'record'}
    mock_log_record = {'test': 'record'}
    mock_record = MockRecord()
    json_formatter = JsonFormatter()
    json_formatter.tracer = 'test_tracer'
    json_formatter.add_fields(mock_log_record, mock_record, {})

    m_format_msg_exc.assert_called_with(mock_record)
    m_generate_log_record.assert_called_with(mock_record, stackdriver=False)
    m_add_span_values.assert_called_with('test_tracer', {'test_generate': 'record'}, stackdriver=False)
    assert mock_log_record == {'test': 'record', 'test_generate': 'record'}


@patch(MODULE_PATH + '_format_message_for_exception')
@patch(MODULE_PATH + '_generate_log_record')
@patch(MODULE_PATH + '_add_span_values')
def test_JsonFormatter_add_fields_stackdriver(m_add_span_values, m_generate_log_record, m_format_msg_exc):
    class MockRecord:
        exc_info = 'test_exc_info'

    m_generate_log_record.return_value = {'test_generate': 'record'}
    mock_log_record = {'test': 'record'}
    mock_record = MockRecord()
    json_formatter = JsonFormatter(stackdriver=True)
    json_formatter.tracer = 'test_tracer'
    json_formatter.add_fields(mock_log_record, mock_record, {})

    m_format_msg_exc.assert_called_with(mock_record)
    m_generate_log_record.assert_called_with(mock_record, stackdriver=True)
    m_add_span_values.assert_called_with('test_tracer', {'test_generate': 'record'}, stackdriver=True)
    assert mock_log_record == {'test': 'record', 'test_generate': 'record'}


def test_generate_log_record_local():
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

    mock_log_record = _generate_log_record(mock_record, stackdriver=False)

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


def test_generate_log_record_stackdriver():
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

    mock_log_record = _generate_log_record(mock_record, stackdriver=True)

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


def test_add_span_values_local():
    m_tracer = MagicMock()
    m_tracer.current_span = {
        'values': {
            'X-B3-TraceId': 'test_trace_id',
            'X-B3-ParentSpanId': 'test_parent_span_id',
            'X-B3-SpanId': 'test_span_id',
            'X-B3-Sampled': 'test_sampled',
            'X-B3-Flags': 'test_b3_flags'
        }}
    m_record = {}
    _add_span_values(m_tracer, m_record, stackdriver=False, project_name='test_project_name')

    assert m_record == {'spanId': 'test_span_id', 'trace': 'test_trace_id'}


def test_add_span_values_stackdriver():
    m_tracer = MagicMock()
    m_tracer.current_span = {
        'values': {
            'X-B3-TraceId': 'test_trace_id',
            'X-B3-ParentSpanId': 'test_parent_span_id',
            'X-B3-SpanId': 'test_span_id',
            'X-B3-Sampled': 'test_sampled',
            'X-B3-Flags': 'test_b3_flags'
        }}
    m_record = {}
    _add_span_values(m_tracer, m_record, stackdriver=True, project_name='test_project_name')

    assert m_record == {'logging.googleapis.com/spanId': 'test_span_id',
                        'logging.googleapis.com/trace': 'projects/test_project_name/traces/test_trace_id'}


def test_add_span_values_none():
    class MockTracer:
        @property
        def current_span(self):
            raise SpanNotStartedError()

    m_tracer = MockTracer()
    m_record = {}
    _add_span_values(m_tracer, m_record, stackdriver=True, project_name='test_project_name')

    assert m_record == {}


@patch(MODULE_PATH + 'traceback')
def test_format_message_for_exception(m_traceback):
    m_record = MagicMock()

    class TestException(Exception):
        pass

    m_record.exc_info = (TestException, 'test_exception', 'test_tb')
    m_traceback.format_tb.return_value = ['test_formatted_tb']
    _format_message_for_exception(m_record)

    m_traceback.format_tb.assert_called_with('test_tb')
    expected_message = """Exception: TestException(test_exception)
Traceback:
test_formatted_tb"""
    assert m_record.message == expected_message


def test_JsonLoggerFactory():
    json_logger_factory = JSONLoggerFactory('test_project_name', 'test_service_name', 'test')

    logger = json_logger_factory.get_logger('test_logger_name')
    assert logger.name == 'test_service_name.test_logger_name'
    assert isinstance(logger.root.handlers[0].formatter, JsonFormatter)
