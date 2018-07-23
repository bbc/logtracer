import logging

from flask import request

from stackdriver_logging.tracing import start_traced_span, end_traced_span


class TracedRoute:
    """
    Decorator to handle starting a span, logging it, closing it, logging it, and logging exceptions.

    If an exception is caught, it is logged to stdout then raised again so the appropriate Flask error handler
    can deal with it.
    """

    def __init__(self, service_name):
        self.service_name = service_name

    def __call__(self, f, *args, **kwargs):
        def log_span(*args, **kwargs):
            start_traced_span(request.headers, request.path)
            logging.getLogger(self.service_name).info(f'{request.method} - {request.url}')
            try:
                response = f(*args, **kwargs)
                logging.getLogger(self.service_name).info(f'{response.status} - {request.url}')
                end_traced_span()
                return response
            except Exception as e:
                logging.getLogger(self.service_name).exception(e)
                end_traced_span()
                raise e

        return log_span
