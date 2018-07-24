import functools

from flask import request

from stackdriver_logging.jsonlog import get_logger
from stackdriver_logging.tracing import start_traced_span, end_traced_span


class TracedRoute:
    """
    Decorator to handle starting a span, logging it, closing it, logging it, and logging exceptions.

    If an exception is caught, it is logged to stdout then raised again so the appropriate Flask error handler
    can deal with it.
    """

    def __call__(self, f, *args, **kwargs):
        @functools.wraps(f)
        def log_span(*args, **kwargs):
            logger = get_logger()
            start_traced_span(request.headers, request.path)
            logger.info(f'{request.method} - {request.url}')
            response, status_number = f(*args, **kwargs)
            logger.info(f'{response.status} - {request.url}')
            end_traced_span()
            return response, status_number

        return log_span


class TracedExceptionHandler:
    def __call__(self, f):
        @functools.wraps(f)
        def log_error_response(e):
            logger = get_logger()
            response = f(e)
            logger.exception(e)
            logger.error(f'{response.status} - {request.url}')
            end_traced_span()
            return response

        return log_error_response


class LogException:
    """For usage with callbacks - cant access exception object in callbacks (if they are handled) so have to add this
    decorator to the error handlers"""
    def __call__(self, f):
        @functools.wraps(f)
        def log_exception(e):
            logger = get_logger()
            response = f(e)
            logger.exception(e)
            return response

        return log_exception
