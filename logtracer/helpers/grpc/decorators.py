import copy
import functools

from logtracer.jsonlog import get_logger
from logtracer.tracing import Tracer


def _rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(_rgetattr(obj, pre) if pre else obj, post, val)


def _rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))


def redact_request(request, fields):
    """
    Returns a copy of the request with sensitive items redacted.
    Does not mutate the original but returns a deep clone.
    """
    r = copy.deepcopy(request)
    if fields:
        for field in fields:
            try:
                _rsetattr(r, field, "REDACTED")
            except AttributeError:
                pass
    return r


class GRPCTracer(Tracer):
    def trace_call(self, redacted_fields=None):
        def trace_call_decorator(f):
            @functools.wraps(f)
            def log_span(self, request, context):
                logger = get_logger(__name__)
                b3_values = getattr(request, 'b3_values', {})
                self.start_traced_span(b3_values, f.__name__)
                logger.info(
                    f"gRPC - Call '{f.__name__}': "
                    f"{redact_request(request, redacted_fields) if request.ListFields() else {}}"
                )
                try:
                    response = f(self, request, context)
                except Exception as e:
                    logger.exception(e)
                    logger.error(f"gRPC - {type(e).__name__} - '{f.__name__}'")
                    self.end_traced_span()
                    raise e
                logger.info(f"gRPC - Return '{f.__name__}'")
                self.end_traced_span()
                return response

            return log_span

        return trace_call_decorator

    def trace_all_calls(self, redacted_fields=None):
        """Apply a decorator to all methods of a Class, excluding `__init__`."""

        def decorate(cls):
            for attr in cls.__dict__:
                if callable(getattr(cls, attr)) and attr != '__init__':
                    def wrapper(f):
                        trace_call_decorator = self.trace_call(redacted_fields)
                        return trace_call_decorator(f)

                    setattr(cls, attr, wrapper(getattr(cls, attr)))
            return cls

        return decorate
