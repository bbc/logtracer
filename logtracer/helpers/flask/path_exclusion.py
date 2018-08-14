from flask import request


def _is_path_excluded(excluded_routes, excluded_routes_partial):
    """
    Decide if, for a particular Flask route, the trace should be posted to the stackdriver API or not.

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