from logtracer.examples.flask.log import logger_factory
from logtracer.helpers.mixed.tracing import MixedTracer

mixed_tracer = MixedTracer(logger_factory, post_spans_to_stackdriver_api=True)
mixed_tracer.set_logging_level('INFO')
