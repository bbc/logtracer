import logging
import time
from threading import Thread

import requests

from examples.flask.server import flask_port, run_flask_server
from logtracer.jsonlog import configure_json_logging, get_logger
from logtracer.tracing import configure_tracing

service_name = 'demoApp'
project_name = 'bbc-connected-data'
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)


def br():
    print('\n')


def start_servers():
    flask_callbacks_server_thread = Thread(target=run_flask_server)
    flask_callbacks_server_thread.start()


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_examples():
    time.sleep(1)
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `start_span_and_log_
    # request_before` which will start a span. This generates both a 32 character trace ID and a 16 character span ID
    # and log the request. It then runs `log_response_after` logs the response code. When the request object is done
    # with, the teardown callback closes the span. Every time `end_span` is called, logs are sent to the Stackdriver
    # Trace API.
    br()
    print('FLASK CALLBACKS EXAMPLE')

    print('Single call to Flask root endpoint:')
    requests.get(f'http://localhost:{flask_port}/')
    print('Done')

    br()
    # Call an endpoint so a span is created, then within that span call another endpoint and pass the tracing
    # parameters. This will create a new subspan with the same trace ID as the initial request and a new span ID will
    # be generated. Confirm this in the log outputs.
    print('Double call to Flask endpoints:')
    requests.get(f'http://localhost:{flask_port}/doublehttp')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the Trace API.
    print('Two calls to endpoints excluded from Trace API:')
    requests.get(f'http://localhost:{flask_port}/exclude-full')
    requests.get(f'http://localhost:{flask_port}/exclude-with-path-var/examplepathvar1')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the logs.
    print('Call to handled exception:')
    requests.get(f'http://localhost:{flask_port}/handledexception')
    print('Call to unhandled exception:')
    requests.get(f'http://localhost:{flask_port}/unhandledexception')
    print('Done')


if __name__ == '__main__':
    print('****** Local formatted examples with non-posted traces ******')
    configure_json_logging(project_name, service_name, 'local')
    configure_tracing(post_spans_to_stackdriver_api=False)
    start_servers()

    logger = get_logger()
    logger.setLevel('DEBUG')

    run_flask_examples()

    br()
    print('****** GCP formatted examples with posted traces ******')
    configure_json_logging(project_name, service_name, 'stackdriver')
    configure_tracing(post_spans_to_stackdriver_api=True)
    logger = get_logger()
    logger.setLevel('DEBUG')

    run_flask_examples()
