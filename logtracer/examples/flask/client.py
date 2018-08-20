import logging

from logtracer.examples.flask.log import logger_factory
from logtracer.examples.flask.server import flask_port
from examples.flask.trace import flask_tracer

logger = logger_factory.get_logger(__name__)
logger.setLevel('DEBUG')

logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_examples():
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `start_span_and_log_
    # request_before` which will start a span. This generates both a 32 character trace ID and a 16 character span ID
    # and log the request. It then runs `log_response_after` logs the response code. When the request object is done
    # with, the teardown callback closes the span. Every time `end_span` is called, logs are sent to the Stackdriver
    # Trace API.
    logger.info('Single call to Flask root endpoint...')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/')

    # Call an endpoint so a span is created, then within that span call another endpoint and pass the tracing
    # parameters. This will create a new subspan with the same trace ID as the initial request and a new span ID will
    # be generated. Confirm this in the log outputs.
    logger.info('Double call to Flask endpoints...')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/doublehttp')

    # Do as the first example but call endpoints which are 'excluded', these should not appear in the Trace API.
    logger.info('Two calls to endpoints excluded from Trace API...')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/exclude-full')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/exclude-with-path-var/examplepathvar1')

    # Call to an endpoint in which an exception is raised and handled by a flask error handler
    logger.info('Call to handled exception...')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/handledexception')

    # Call to an endpoint where an exception is raised and not caught by a flask error handler
    logger.info('Call to unhandled exception...')
    flask_tracer.requests.get(f'http://localhost:{flask_port}/unhandledexception')


if __name__ == '__main__':
    flask_tracer.start_traced_span({}, 'run_examples')

    run_flask_examples()

    flask_tracer.end_traced_span(exclude_from_posting=False)
