from logtracer.examples.grpc.log import logger_factory
from logtracer.helpers.grpc.tracing import GRPCTracer

grpc_tracer = GRPCTracer(
    logger_factory,
    post_spans_to_stackdriver_api=True,
    redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1']
)
grpc_tracer.set_logging_level('DEBUG')
