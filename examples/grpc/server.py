import time
from concurrent import futures

import grpc

from examples.grpc.resources import grpc_demo_pb2_grpc, grpc_demo_pb2
from logtracer.helpers.grpc.tracer import GRPCTracer
from logtracer.jsonlog import JSONLoggerFactory

ONE_DAY_IN_SECONDS = 60 * 60 * 24

project_name = 'bbc-connected-data'
service_name = 'demoApp'

logger_factory = JSONLoggerFactory(project_name, service_name, 'local')

grpc_tracer = GRPCTracer(
    logger_factory,
    post_spans_to_stackdriver_api=False,
    redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1']
)
grpc_tracer.set_logging_level('DEBUG')

logger = logger_factory.get_logger('demoGRPCLogger')
logger.setLevel('DEBUG')

grpc_port = 50055


class HandledException(Exception):
    pass


class UnhandledException(Exception):
    pass


def handle_exceptions(f):
    def wrapper(self, request, context):
        try:
            return f(self, request, context)
        except HandledException:
            context.abort(grpc.StatusCode.INTERNAL, 'Handled exception, closing context')

    return wrapper


def handle_exception_for_all_methods():
    """Apply a decorator to all methods of a Class, excluding `__init__`."""

    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr != '__init__':
                setattr(cls, attr, handle_exceptions(getattr(cls, attr)))
        return cls

    return decorate


@handle_exception_for_all_methods()
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    def DemoRPC(self, request, context):
        logger.info('Demo Empty RPC call')
        time.sleep(2)
        logger.info('Call done')
        return grpc_demo_pb2.EmptyMessage()

    def DemoRPCHandledException(self, request, context):
        logger.info('Demo Handled Exception RPC call')
        time.sleep(2)
        raise HandledException('This is a handled exception!')

    def DemoRPCUnHandledException(self, request, context):
        logger.info('Demo Unhandled Exception RPC call')
        time.sleep(2)
        raise UnhandledException('This is an unhandled exception!')

    # @trace_call(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
    def DemoRPCRedactedParameters(self, request, context):
        logger.info('Demo RPC call with redacted parameters')
        time.sleep(2)
        logger.info('Call done')
        return grpc_demo_pb2.EmptyMessage()


def create_server(grpc_port):
    interceptor = grpc_tracer.server_interceptor()
    server = grpc.server(
        futures.ThreadPoolExecutor(),
        interceptors=(interceptor,)
    )
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


if __name__ == '__main__':
    run_grpc_server()
