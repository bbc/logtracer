import logging
import time

import grpc
from grpc._channel import _Rendezvous

from logtracer.examples.grpc.resources.grpc_demo_pb2 import DemoMessage, EmptyMessage, NestedMessage, DoubleNestedMessage
from logtracer.examples.grpc.resources.grpc_demo_pb2_grpc import DemoServiceStub
from logtracer.examples.grpc.server import grpc_port
from examples.grpc.trace import grpc_tracer

logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)


def run_grpc_examples(stub):
    time.sleep(1)
    # Call the Demo rpc of the gRPC server. On receiving the request, the `log_event` decorator will will start a span
    # and log it. It then closes the span and logs it.

    print('GRPC EXAMPLE')

    # call with redacted values
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

    print('Call to gRPC endpoint:')
    message = EmptyMessage()
    stub.DemoRPC(message)

    # call to handled exception
    print('Call to handled exception endpoint:')
    message = EmptyMessage()
    try:
        stub.DemoRPCHandledException(message)
    except _Rendezvous as e:
        print(e.code(), e.details())

    # call to unhandled exception
    print('Call to unhandled exception endpoint:')
    message = EmptyMessage()
    try:
        stub.DemoRPCUnHandledException(message)
    except _Rendezvous as e:
        print(e.code(), e.details())


if __name__ == '__main__':
    print('****** Local formatted examples with non-posted traces ******')
    channel = grpc.insecure_channel(f'localhost:{grpc_port}')
    intercept_channel = grpc.intercept_channel(channel, grpc_tracer.client_interceptor())
    stub = DemoServiceStub(intercept_channel)

    grpc_tracer.start_traced_span({}, 'run_examples')
    run_grpc_examples(stub)
    grpc_tracer.end_traced_span(exclude_from_posting=False)
