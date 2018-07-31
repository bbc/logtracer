import functools

from logtracer.jsonlog import get_logger


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
