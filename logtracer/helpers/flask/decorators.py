import functools

from flask import request

from logtracer.jsonlog import get_logger
from logtracer.tracing import start_traced_span, end_traced_span


def trace_and_log_route(f):
    """
    Decorator to handle starting a span, logging/tracing it, closing it, and logging/tracing it.
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_traced_span(request.headers, request.path)
        logger.info(f'{request.method} - {request.url}')
        response, status_number = f(*args, **kwargs)
        logger.info(f'{response.status} - {request.url}')
        end_traced_span()
        return response, status_number

    return wrapper


def trace_and_log_exception(exception_handler):
    """
    Decorator for flask exception handlers to close and log spans.
    """

    @functools.wraps(exception_handler)
    def wrapper(e):
        logger = get_logger()
        response = exception_handler(e)
        logger.exception(e)
        logger.error(f'{response.status} - {request.url}')
        end_traced_span()
        return response

    return wrapper


def log_exception(f):
    """
    For usage with `logtracer.helpers.flask.callbacks` - cant access exception object in callbacks if they are handled
    by an exception handlers so add this decorator to any of your Flask exception handlers to make sure the stack
    traces are logged.
    """

    @functools.wraps(f)
    def wrapper(e):
        logger = get_logger()
        response = f(e)
        logger.exception(e)
        return response

    return wrapper
