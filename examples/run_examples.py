import logging
from threading import Thread

import grpc
import requests
import time

from examples.flask_server import flask_port, run_flask_server
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


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_examples():
    server_thread = Thread(target=run_flask_server)
    server_thread.start()

    time.sleep(1)
    # Call the root endpoint of the Flask server. On receiving the request, the server will run `before_request` which
    # will start a span. This generates both a 32 character trace ID and a 16 character span ID and log the request. It
    # then runs `after_request` which closes the span. Every time `end_span` is called, logs are sent to the
    # Stackdriver Trace API.
    print('\n\n')
    logger.info('Single call to Flask root endpoint:')
    requests.get(f'http://localhost:{flask_port}/')
    logger.info('Done')

    print('\n\n')
    # Create a span as above, then pass those tracing parameters to a call to the root endpoint. This will create a new
    # subspan with the same trace ID as the initial request and a new span ID will be generated. Confirm this in the
    # log outputs.
    logger.info('Double call to Flask endpoints:')
    requests.get(f'http://localhost:{flask_port}/doublehttp')
    logger.info('Done')


def run_grpc_examples():
    server_thread = Thread(target=run_grpc_server)
    server_thread.start()

    time.sleep(1)
    # Call the Demo rpc of the gRPC server. On receiving the request, the `log_event` decorator will will start a span
    # and log it. It then closes the span and logs it.
    print('\n\n')
    logger.info('Call to gRPC endpoint:')
    message = DemoMessage()
    stub.DemoRPC(message)

    print('\n\n')
    # Call a Flask endpoint which creates a span and passes the parameters to the RPC Demo endpoint where a subspan
    # is created with the same trace ID but a new span ID.
    logger.info('Call to Flask endpoint that calls gRPC endpoint:')
    requests.get(f'http://localhost:{flask_port}/grpc')
    logger.info('Done')


if __name__ == '__main__':
    run_flask_examples()
    # run_grpc_examples()
