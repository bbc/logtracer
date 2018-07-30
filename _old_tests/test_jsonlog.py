import logging

from logtrace import _global_vars
from logtrace.jsonlog import configure_json_logging, StackdriverJsonFormatter


def test_configure_json_logging():
    root_logger = logging.getLogger()
    assert _global_vars.gcp_project_name == ''
    configure_json_logging('project_name')
    assert isinstance(root_logger.handlers[1].formatter, StackdriverJsonFormatter)
    assert _global_vars.gcp_project_name == 'project_name'
