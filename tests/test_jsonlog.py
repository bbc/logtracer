import logging

from gcptracelogging import global_vars
from gcptracelogging.jsonlog import configure_json_logging, CustomJsonFormatter


def test_configure_json_logging():
    root_logger = logging.getLogger()
    assert global_vars.gcp_project_name == ''
    configure_json_logging('project_name')
    assert isinstance(root_logger.handlers[1].formatter, CustomJsonFormatter)
    assert global_vars.gcp_project_name == 'project_name'
