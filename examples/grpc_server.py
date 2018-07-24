import logging
import time
from concurrent import futures

import grpc

from examples.grpc_resources import grpc_demo_pb2_grpc, grpc_demo_pb2
from stackdriver_logging.grpc_helpers.decorators import trace_call

ONE_DAY_IN_SECONDS = 60 * 60 * 24
logger = logging.getLogger('demoGRPCLogger')
logger.setLevel('DEBUG')
grpc_port = 50055


class HandledException(Exception):
    pass


class UnhandledException(Exception):
    pass


def handle_exceptions(f):
    def wrapper(self, request, context):
        try:
            f(self, request, context)
        except HandledException:
            context.abort(grpc.StatusCode.INTERNAL, 'Handled exception, closing context')

    return wrapper


class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    @trace_call()
    def DemoRPC(self, request, context):
        # do stuff here
        return grpc_demo_pb2.EmptyMessage()

    @handle_exceptions
    @trace_call()
    def DemoRPCHandledException(self, request, context):
        raise HandledException('This is a handled exception!')

    @trace_call()
    def DemoRPCUnHandledException(self, request, context):
        raise UnhandledException('This is an unhandled exception!')

    @trace_call(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
    def DemoRPCRedactedParameters(self, request, context):
        return grpc_demo_pb2.EmptyMessage()


def create_server(grpc_port):
    server = grpc.server(futures.ThreadPoolExecutor())
    grpc_demo_pb2_grpc.add_DemoServiceServicer_to_server(DemoRPC(), server)
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f'Starting gRPC server on http://localhost:{grpc_port}.')
    return server


def run_grpc_server():
    server = create_server(grpc_port)
    try:
        while True:
            time.sleep(ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
