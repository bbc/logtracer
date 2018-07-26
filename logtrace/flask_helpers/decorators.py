import functools

from flask import request

from logtrace.jsonlog import get_logger
from logtrace.tracing import start_traced_span, end_traced_span


def trace_and_log_route(f):
    """
    Decorator to handle starting a span, logging it, closing it, logging it, and logging exceptions.

    If an exception is caught, it is logged to stdout then raised again so the appropriate Flask error handler
    can deal with it.
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


def trace_and_log_exception(f):
    @functools.wraps(f)
    def wrapper(e):
        logger = get_logger()
        response = f(e)
        logger.exception(e)
        logger.error(f'{response.status} - {request.url}')
        end_traced_span()
        return response

    return wrapper


def log_exception(f):
    """For usage with callbacks - cant access exception object in callbacks (if they are handled) so have to add this
    decorator to the error handlers"""
    @functools.wraps(f)
    def wrapper(e):
        logger = get_logger()
        response = f(e)
        logger.exception(e)
        return response

    return wrapper
