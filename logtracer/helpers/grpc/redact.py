import copy
import functools


def _rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(_rgetattr(obj, pre) if pre else obj, post, val)


def _rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))


def redact_request(request, fields):
    """
    Returns a copy of the request with sensitive items redacted.
    Does not mutate the original but returns a deep clone.
    """
    r = copy.deepcopy(request)
    if fields:
        for field in fields:
            try:
                _rsetattr(r, field, "REDACTED")
            except AttributeError:
                pass
    return r