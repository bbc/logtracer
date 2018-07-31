from flask import request

from logtracer.jsonlog import get_logger
from logtracer.tracing import start_traced_span, end_traced_span


def start_span_and_log_request_before(excluded_routes=None, excluded_routes_partial=None):
    """
    Start a span and log the incoming request.

    For use with flask `before_request()` callback, see readme for example usage.
    """

    def execute_before_request():
        if not _is_path_excluded(excluded_routes, excluded_routes_partial):
            start_traced_span(request.headers, request.path)
            get_logger().info(f'{request.method} - {request.url}')

    return execute_before_request


def log_response_after(excluded_routes=None, excluded_routes_partial=None):
    """
    Log the response status.

    For use with flask `after_request()` callback, see readme for example usage.
    """

    def execute_after_request(response):
        if not _is_path_excluded(excluded_routes, excluded_routes_partial):
            logger = get_logger()
            status = str(response.status_code)
            if status[0] in ['4', '5']:
                logger.error(f'{response.status} - {request.url}')
            else:
                logger.info(f'{response.status} - {request.url}')
            return response

    return execute_after_request


def close_span_on_teardown(excluded_routes=None, excluded_routes_partial=None):
    """
    Close the span when the request is torn down (finished).

    For use with flask `teardown_request()` callback, see readme for example usage.
    """

    def execute_on_teardown(_):
        if not _is_path_excluded(excluded_routes, excluded_routes_partial):
            end_traced_span()

    return execute_on_teardown


def _is_path_excluded(excluded_routes, excluded_routes_partial):
    """
    Decide if the Flask route should be traced & logged or not.

    Args:
        path (str):                         Flask route being accessed
        excluded_routes ([str,]):           _full_ routes to exclude
        excluded_routes_partial ([str,]):   partial routes to explore, useful if the route has path variales,
            eg use ['/app-config/config/'] to match '/app-config/<platform>/<version>/config.json'
    """

    exclude = False
    if excluded_routes and request.path in excluded_routes:
        exclude = True
    elif excluded_routes_partial:
        for excluded_route_partial in excluded_routes_partial:
            if excluded_route_partial in request.path:
                exclude = True
                break
    return exclude
