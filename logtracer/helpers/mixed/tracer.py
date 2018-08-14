from logtracer.helpers.flask.tracer import FlaskTracer
from logtracer.helpers.grpc.tracer import GRPCTracer


class MixedTracer(GRPCTracer, FlaskTracer):
    def __init__(self, logger_factory, post_spans_to_stackdriver_api=False):
        """
        Tracer for a Flask App that calls a gRPC app.

        Omits the `redacted_fields` argument of GRPCTracer init as field redaction only takes place on a gRPC server,
        not a gRPC client.
        """

        super().__init__(logger_factory, post_spans_to_stackdriver_api)

