from flask import Flask

from logtracer.helpers.flask.flask_tracing import FlaskTracer
from logtracer.jsonlog import JSONLoggerFactory


def build_app(post_spans_to_stackdriver_api=False):
    project_name = 'bbc-connected-data'
    service_name = 'demoApp'

    logger_handler = JSONLoggerFactory(project_name, service_name, 'local')

    flask_tracer = FlaskTracer(logger_handler, post_spans_to_stackdriver_api=post_spans_to_stackdriver_api)
    flask_tracer.set_logging_level('DEBUG')

    app = Flask('demoFlaskApp')

    app.before_request(flask_tracer.start_span_and_log_request_before())
    app.after_request(flask_tracer.log_response_after())
    app.teardown_request(
        flask_tracer.close_span_and_post_on_teardown(
            excluded_routes=['/exclude-full'],
            excluded_partial_routes=['/exclude-with-path-var']
        )
    )
    return app, flask_tracer, logger_handler
