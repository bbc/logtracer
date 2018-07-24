import logging
import time
from threading import Thread

import grpc
import requests

from examples.flask_server_callbacks import flask_callbacks_port, run_flask_server_callbacks
from examples.flask_server_decorators import run_flask_server_decorators, flask_decorators_port
from examples.grpc_resources.grpc_demo_pb2 import DemoMessage
from examples.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc_server import run_grpc_server, grpc_port
from stackdriver_logging.jsonlog import configure_json_logging, get_logger

# logging
service_name = 'demoApp'
configure_json_logging('bbc-connected-data', service_name)
logger = get_logger()
logger.setLevel('DEBUG')
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)

# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


def br():
    print('\n\n')


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_callbacks_examples():
    br()
    server_thread = Thread(target=run_flask_server_callbacks)
    server_thread.start()

    time.sleep(1)
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `before_request` which
    # will start a span. This generates both a 32 character trace ID and a 16 character span ID and log the request. It
    # then runs `after_request` logs the response code. When the request object is done with, the teardown callack
    # closes the span. Every time `end_span` is called, logs are sent to the Stackdriver Trace API.
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
    br()
    server_thread = Thread(target=run_flask_server_decorators)
    server_thread.start()

    time.sleep(2)
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `before_request` which
    # will start a span. This generates both a 32 character trace ID and a 16 character span ID and log the request. It
    # then runs `after_request` logs the response code. When the request object is done with, the teardown callack
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
    br()
    server_thread = Thread(target=run_grpc_server)
    server_thread.start()
    print('GRPC EXAMPLE')

    time.sleep(2)
    # Call the Demo rpc of the gRPC server. On receiving the request, the `log_event` decorator will will start a span
    # and log it. It then closes the span and logs it.
    br()
    print('Call to gRPC endpoint:')
    message = DemoMessage()
    stub.DemoRPC(message)

    # call to handled exception

    # call to unhandled exception

    # call with redacted cookie

    br()
    # Call a Flask endpoint which creates a span and passes the parameters to the RPC Demo endpoint where a subspan
    # is created with the same trace ID but a new span ID.
    print('Call to Flask endpoint that calls gRPC endpoint:')
    requests.get(f'http://localhost:{flask_callbacks_port}/grpc')
    print('Done')


if __name__ == '__main__':
    # run_flask_decorators_examples()
    run_flask_callbacks_examples()
    run_grpc_examples()
