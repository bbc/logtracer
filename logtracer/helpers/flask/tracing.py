import functools

from flask import request

from logtracer.helpers.flask.path_exclusion import _is_path_excluded
from logtracer.tracing import Tracer


class FlaskTracer(Tracer):
    def start_span_and_log_request_before(self):
        """
        Start a span and log the incoming request.

        For use with flask `before_request()` callback, see readme for example usage.
        """

        def execute_before_request():
            self.start_traced_span(request.headers, request.path)
            self.logger.info(f'{request.method} - {request.url}')

        return execute_before_request

    def log_response_after(self):
        """
        Log the response status.

        For use with flask `after_request()` callback, see readme for example usage.
        """

        def execute_after_request(response):
            status = str(response.status_code)
            if status[0] in ['4', '5']:
                self.logger.error(f'{response.status} - {request.url}')
            else:
                self.logger.info(f'{response.status} - {request.url}')
            return response

        return execute_after_request

    def close_span_and_post_on_teardown(self, excluded_routes=None, excluded_partial_routes=None):
        """
        Close the span when the request is torn down (finished).

        Arguments:
            excluded_routes [str,]:
            excluded_partial_routes [str,]:

        For use with flask `teardown_request()` callback, see readme for example usage.
        """

        if (excluded_routes and not isinstance(excluded_routes, list)) or \
                (excluded_partial_routes and not isinstance(excluded_partial_routes, list)):
            raise ValueError('Excluded routes must be a list.')

        def execute_on_teardown(_):
            self.end_traced_span(_is_path_excluded(excluded_routes, excluded_partial_routes))

        return execute_on_teardown

    def log_exception(self, f):
        """
        Decorator to be used with Flask error handlers to log exception stack traces.
        """

        @functools.wraps(f)
        def wrapper(e):
            response = f(e)
            self.logger.exception(e)
            return response

        return wrapper
