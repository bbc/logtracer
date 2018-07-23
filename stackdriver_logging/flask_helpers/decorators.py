import functools
import logging

from flask import request

from stackdriver_logging import global_vars
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
            logger = logging.getLogger(global_vars.service_name)
            start_traced_span(request.headers, request.path)
            logger.info(f'{request.method} - {request.url}')
            try:
                response, status_number = f(*args, **kwargs)
                logger.info(f'{response.status} - {request.url}')
                end_traced_span()
                return response, status_number
            except Exception as e:
                logger.exception(e)
                end_traced_span()
                raise e

        return log_span
