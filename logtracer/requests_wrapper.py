from copy import deepcopy

import requests


class RequestsWrapper:
    def __init__(self, tracer):
        """Wraps the requests library to automatically attach tracing information to outgoing headers."""
        self.tracer = tracer
        request_methods = [method for method in dir(requests.api) if not method.startswith('_')]

        def wrapped_request(method):
            def wrapper(*args, **kwargs):
                headers = deepcopy(kwargs.get('headers', {}))
                headers.update(self.tracer.generate_new_traced_subspan_values())
                kwargs['headers'] = headers
                self.tracer.logger.info(f'OUTBOUND {method.upper()} - {args[0]}')
                response = getattr(requests, method)(*args, **kwargs)
                self.tracer.logger.info(f'{response.status_code} {response.reason} - {args[0]}')
                return response

            return wrapper

        for method in request_methods:
            setattr(self, method, wrapped_request(method))


class UnsupportedRequestsWrapper:
    def __init__(self, tracer):
        """Wraps the requests library to automatically attach tracing information to outgoing headers."""
        from logtracer.tracing import SubSpanContext

        self.tracer = tracer
        request_methods = [method for method in dir(requests.api) if not method.startswith('_')]

        def wrapped_request(method):
            def wrapper(*args, **kwargs):
                url = args[0]
                with SubSpanContext(tracer, url):
                    self.tracer.logger.info(f'OUTBOUND {method.upper()} - {url}')
                    response = getattr(requests, method)(*args, **kwargs)
                    self.tracer.logger.info(f'{response.status_code} {response.reason} - {url}')
                return response

            return wrapper

        for method in request_methods:
            setattr(self, method, wrapped_request(method))
