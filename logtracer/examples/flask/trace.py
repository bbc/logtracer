from logtracer.examples.flask.log import logger_factory
from logtracer.helpers.flask.tracing import FlaskTracer

flask_tracer = FlaskTracer(logger_factory, post_spans_to_stackdriver_api=True)
flask_tracer.set_logging_level('INFO')
