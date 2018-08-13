import json

import grpc
from grpc._cython.cygrpc import _Metadatum
from grpc._interceptor import _ClientCallDetails

from logtracer.helpers.grpc.redact import redact_request
from logtracer.tracing import Tracer

B3_VALUE_KEY = 'b3-values'


class GRPCTracer(Tracer):

    def __init__(self, json_logger_handler, post_spans_to_stackdriver_api=False, redacted_fields=None):
        super().__init__(json_logger_handler, post_spans_to_stackdriver_api)
        self.redacted_fields = redacted_fields if redacted_fields is not None else []

    def incoming_server_interceptor(self):
        return _IncomingInterceptor(self)

    def outgoing_client_interceptor(self):
        return _OutgoingInterceptor(self)


class _IncomingInterceptor(grpc.ServerInterceptor):

    def __init__(self, tracer):
        self._tracer = tracer

    def intercept_service(self, continuation, handler_call_details):
        def tracing_wrapper(behavior, *_):
            def new_behaviour(request, servicer_context):

                b3_values = self._retrieve_b3_values_from_incoming_call(handler_call_details)

                self._tracer.start_traced_span(b3_values, handler_call_details.method)
                redacted_request_str = f"\nrequest: {redact_request(request, self._tracer.redacted_fields)}" \
                    if request.ListFields() else ''

                self._tracer.logger.info(
                    f'{handler_call_details.method} - received gRPC call {redacted_request_str}'
                )

                exception_raised = False
                try:
                    return behavior(request, servicer_context)
                except Exception as e:
                    status_str = _grpc_status_from_context(servicer_context)
                    self._tracer.logger.error(f"{handler_call_details.method} - {type(e).__name__}{status_str}")
                    self._tracer.logger.exception(e)
                    self._tracer.end_traced_span(exclude_from_posting=False)
                    exception_raised = True
                    raise e
                finally:
                    if not exception_raised:
                        status_str = _grpc_status_from_context(servicer_context)
                        self._tracer.logger.info(f'{handler_call_details.method}{status_str} - returning gRPC call')
                        self._tracer.end_traced_span(exclude_from_posting=False)

            return new_behaviour

        return _wrap_rpc_behavior(continuation(handler_call_details), tracing_wrapper)

    @staticmethod
    def _retrieve_b3_values_from_incoming_call(handler_call_details):
        b3_values = {}
        for metadatum in handler_call_details.invocation_metadata:
            if metadatum.key == B3_VALUE_KEY:
                b3_values = json.loads(metadatum.value)
        return b3_values


class _OutgoingInterceptor(grpc.UnaryUnaryClientInterceptor):

    def __init__(self, tracer):
        self._tracer = tracer

    def intercept_unary_unary(self, continuation, client_call_details, request):
        self._tracer.logger.info(f'{client_call_details.method} - outbound gRPC call')

        metadata = self._generate_metadata_with_b3_values(client_call_details)

        client_call_details = _ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials
        )

        response_future = continuation(client_call_details, request)
        response_future.result()
        self._tracer.logger.info(f'Response received from {client_call_details.method}.')
        return response_future

    def _generate_metadata_with_b3_values(self, client_call_details):
        subspan_values = self._tracer.generate_new_traced_subspan_values()
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        b3_metadatum = _Metadatum(key=B3_VALUE_KEY, value=json.dumps(subspan_values))
        metadata.append(b3_metadatum)
        return metadata


def _grpc_status_from_context(servicer_context):
    if servicer_context._state.code is not None:
        return f" - {servicer_context._state.code} - {str(servicer_context._state.details)}"
    else:
        return ''


def _wrap_rpc_behavior(handler, fn):
    behavior_fn = handler.unary_unary
    handler_factory = grpc.unary_unary_rpc_method_handler

    new_rpc_handler = handler_factory(
        fn(
            behavior_fn,
            handler.request_streaming,
            handler.response_streaming
        ),
        request_deserializer=handler.request_deserializer,
        response_serializer=handler.response_serializer
    )

    return new_rpc_handler
