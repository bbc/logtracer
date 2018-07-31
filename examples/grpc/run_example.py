import logging
import time
from threading import Thread

import grpc
import requests
from grpc._channel import _Rendezvous

from examples.flask.server import flask_port, run_flask_server
from examples.grpc.resources.grpc_demo_pb2 import DemoMessage, EmptyMessage, NestedMessage, DoubleNestedMessage
from examples.grpc.resources.grpc_demo_pb2_grpc import DemoServiceStub
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
    print('\n')


def start_servers():
    grpc_server_thread = Thread(target=run_grpc_server)
    grpc_server_thread.start()
    flask_server_thread = Thread(target=run_flask_server)
    flask_server_thread.start()
    time.sleep(2)


def run_grpc_examples():
    time.sleep(1)
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
    requests.get(f'http://localhost:{flask_port}/grpc')
    print('Done')


if __name__ == '__main__':
    print('****** Local formatted examples with non-posted traces ******')
    configure_json_logging(project_name, service_name, 'local')
    configure_tracing(post_spans_to_stackdriver_api=False)
    start_servers()

    logger = get_logger()
    logger.setLevel('DEBUG')

    run_grpc_examples()

    print('****** GCP formatted examples with posted traces ******')
    configure_json_logging(project_name, service_name, 'stackdriver')
    configure_tracing(post_spans_to_stackdriver_api=True)
    logger = get_logger()
    logger.setLevel('DEBUG')

    run_grpc_examples()
