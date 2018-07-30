import logging
import time
from threading import Thread

import grpc
import requests
from grpc._channel import _Rendezvous

from examples.flask.server_callbacks import flask_callbacks_port, run_flask_server_callbacks
from examples.flask.server_decorators import run_flask_server_decorators, flask_decorators_port
from examples.grpc.grpc_resources.grpc_demo_pb2 import DemoMessage, EmptyMessage, NestedMessage, DoubleNestedMessage
from examples.grpc.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc.server import run_grpc_server, grpc_port
from logtracer.jsonlog import configure_json_logging, get_logger
# logging
from logtracer.tracing import configure_tracing

service_name = 'demoApp'
project_name = 'bbc-connected-data'
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)

# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


def br():
    print('\n\n')


def start_servers():
    flask_callbacks_server_thread = Thread(target=run_flask_server_callbacks)
    flask_callbacks_server_thread.start()
    flask_server_decorators_server_thread = Thread(target=run_flask_server_decorators)
    flask_server_decorators_server_thread.start()
    grpc_server_thread = Thread(target=run_grpc_server)
    grpc_server_thread.start()
    time.sleep(2)


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_callbacks_examples():
    time.sleep(1)
    br()
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `start_span_and_log_
    # request_before` which will start a span. This generates both a 32 character trace ID and a 16 character span ID
    # and log the request. It then runs `log_response_after` logs the response code. When the request object is done
    # with, the teardown callback closes the span. Every time `end_span` is called, logs are sent to the Stackdriver
    # Trace API.
    br()
    print('FLASK CALLBACKS EXAMPLE')

    print('Single call to Flask root endpoint:')
    requests.get(f'http://localhost:{flask_callbacks_port}/')
    print('Done')

    br()
    # Create a span as above, then pass those tracing parameters to a call to the root endpoint. This will create a new
    # subspan with the same trace ID as the initial request and a new span ID will be generated. Confirm this in the
    # log outputs.
    print('Double call to Flask endpoints:')
    requests.get(f'http://localhost:{flask_callbacks_port}/doublehttp')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the logs.
    print('Two calls to excluded endpoints:')
    requests.get(f'http://localhost:{flask_callbacks_port}/excludefull')
    requests.get(f'http://localhost:{flask_callbacks_port}/excludepartial')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the logs.
    print('Call to handled exception:')
    requests.get(f'http://localhost:{flask_callbacks_port}/handledexception')
    print('Call to unhandled exception:')
    requests.get(f'http://localhost:{flask_callbacks_port}/unhandledexception')
    print('Done')


def run_flask_decorators_examples():
    time.sleep(1)
    br()
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `start_span_and_log_request_before` which
    # will start a span. This generates both a 32 character trace ID and a 16 character span ID and log the request. It
    # then runs `log_response_after` logs the response code. When the request object is done with, the teardown callack
    # closes the span. Every time `end_span` is called, logs are sent to the Stackdriver Trace API.
    br()
    print('FLASK DECORATORS EXAMPLE')
    print('Single call to Flask root endpoint:')
    requests.get(f'http://localhost:{flask_decorators_port}/')
    print('Done')

    br()
    # Create a span as above, then pass those tracing parameters to a call to the root endpoint. This will create a new
    # subspan with the same trace ID as the initial request and a new span ID will be generated. Confirm this in the
    # log outputs.
    print('Double call to Flask endpoints:')
    requests.get(f'http://localhost:{flask_decorators_port}/doublehttp')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the logs.
    print('Call to excluded endpoint:')
    requests.get(f'http://localhost:{flask_decorators_port}/exclude')
    print('Done')

    br()
    # Do as the first example but call endpoints which are 'excluded', these should not appear in the logs.
    print('Call to handled exception:')
    requests.get(f'http://localhost:{flask_decorators_port}/handledexception')
    print('Call to unhandled exception:')
    requests.get(f'http://localhost:{flask_decorators_port}/unhandledexception')
    print('Done')


def run_grpc_examples():
    time.sleep(1)
    br()
    # Call the Demo rpc of the gRPC server. On receiving the request, the `log_event` decorator will will start a span
    # and log it. It then closes the span and logs it.
    br()
    print('GRPC EXAMPLE')
    print('Call to gRPC endpoint:')
    message = EmptyMessage()
    stub.DemoRPC(message)

    # call to handled exception
    br()
    print('Call to handled exception endpoint:')
    message = EmptyMessage()
    try:
        stub.DemoRPCHandledException(message)
    except _Rendezvous as e:
        print(e.code(), e.details())

    # call to unhandled exception
    br()
    print('Call to unhandled exception endpoint:')
    message = EmptyMessage()
    try:
        stub.DemoRPCUnHandledException(message)
    except _Rendezvous as e:
        print(e.code(), e.details())

    # call with redacted values
    br()
    print('Call to endpoint with redacted values:')
    message = DemoMessage(
        value1='1',
        value2='2',
        nested=NestedMessage(
            nestedvalue1='1',
            nestedvalue2='2',
            doublenested=DoubleNestedMessage(
                doublenestedvalue1='1',
                doublenestedvalue2='2'
            )
        )
    )
    stub.DemoRPCRedactedParameters(message)

    # Call a Flask endpoint which creates a span and passes the parameters to the RPC Demo endpoint where a subspan
    # is created with the same trace ID but a new span ID.
    br()
    print('Call to Flask endpoint that calls gRPC endpoint:')
    requests.get(f'http://localhost:{flask_callbacks_port}/grpc')
    print('Done')


if __name__ == '__main__':
    print('****** Local formatted examples with posted traces ******')
    configure_json_logging(project_name, service_name, 'local')
    configure_tracing(post_spans_to_api=False)
    start_servers()

    logger = get_logger()
    logger.setLevel('DEBUG')

    run_flask_decorators_examples()
    run_flask_callbacks_examples()
    run_grpc_examples()

    print('****** GCP formatted examples with posted traces ******')
    configure_json_logging(project_name, service_name, 'stackdriver')
    configure_tracing(post_spans_to_api=True)
    logger = get_logger()
    logger.setLevel('DEBUG')

    run_flask_decorators_examples()
    run_flask_callbacks_examples()
    run_grpc_examples()
