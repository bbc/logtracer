import logging

import requests

from examples.flask.server import flask_port
from logtracer.jsonlog import JSONLoggerHandler
from logtracer.tracing import Tracer

project_name = 'bbc-connected-data'
service_name = 'demoApp'

logger_handler = JSONLoggerHandler(project_name, service_name, 'local')
logger = logger_handler.get_logger(__name__)
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
    requests.get(f'http://localhost:{flask_port}/', headers=tracer.generate_new_traced_subspan_values())

    # Call an endpoint so a span is created, then within that span call another endpoint and pass the tracing
    # parameters. This will create a new subspan with the same trace ID as the initial request and a new span ID will
    # be generated. Confirm this in the log outputs.
    logger.info('Double call to Flask endpoints...')
    requests.get(f'http://localhost:{flask_port}/doublehttp', headers=tracer.generate_new_traced_subspan_values())

    # Do as the first example but call endpoints which are 'excluded', these should not appear in the Trace API.
    logger.info('Two calls to endpoints excluded from Trace API...')
    requests.get(f'http://localhost:{flask_port}/exclude-full', headers=tracer.generate_new_traced_subspan_values())
    requests.get(f'http://localhost:{flask_port}/exclude-with-path-var/examplepathvar1',
                 headers=tracer.generate_new_traced_subspan_values())

    # Call to an endpoint in which an exception is raised and handled by a flask error handler
    logger.info('Call to handled exception...')
    requests.get(f'http://localhost:{flask_port}/handledexception', headers=tracer.generate_new_traced_subspan_values())

    # Call to an endpoint where an exception is raised and not caught by a flask error handler
    logger.info('Call to unhandled exception...')
    requests.get(f'http://localhost:{flask_port}/unhandledexception',
                 headers=tracer.generate_new_traced_subspan_values())


if __name__ == '__main__':
    tracer = Tracer(logger_handler, post_spans_to_stackdriver_api=False)
    tracer.set_logging_level('DEBUG')

    tracer.start_traced_span({}, 'run_examples')

    run_flask_examples()

    tracer.end_traced_span(exclude_from_posting=False)
