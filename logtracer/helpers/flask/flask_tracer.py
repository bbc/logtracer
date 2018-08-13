import functools

from flask import request

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

        For use with flask `teardown_request()` callback, see readme for example usage.
        """

        def execute_on_teardown(_):
            self.end_traced_span(_is_path_excluded(excluded_routes, excluded_partial_routes))

        return execute_on_teardown

    def log_exception(self, f):
        """
        For usage with `logtracer.helpers.flask.callbacks` - cant access exception object in callbacks if they are handled
        by an exception handlers so add this decorator to any of your Flask exception handlers to make sure the stack
        traces are logged.
        """

        @functools.wraps(f)
        def wrapper(e):
            response = f(e)
            self.logger.exception(e)
            return response

        return wrapper


def _is_path_excluded(excluded_routes, excluded_routes_partial):
    """
    Decide if the Flask route should be traced & logged or not.

    Args:
        excluded_routes ([str,]):           _full_ routes to exclude
        excluded_routes_partial ([str,]):   partial routes to explore, useful if the route has path variales,
            eg use ['/app-config/config/'] to match '/app-config/<platform>/<version>/config.json'
    """
    if (excluded_routes and not isinstance(excluded_routes, list)) or \
            (excluded_routes_partial and not isinstance(excluded_routes_partial, list)):
        raise ValueError('Excluded routes must be in a list.')
    exclude = False
    if excluded_routes and request.path in excluded_routes:
        exclude = True
    elif excluded_routes_partial:
        for excluded_route_partial in excluded_routes_partial:
            if excluded_route_partial in request.path:
                exclude = True
                break
    return exclude
