utilities designed to make integration with a flask microservice easier

requires flask to be installed - likely already installed on module workig on

two ways to start and end spans: callbacks and decorators

when to use either?
use callbacks when you want to log most of the endpoints
use decorators whe you only want to log a few

way to start a subspan: 



callacks.py:

These are helpers to make integration with Flask easier.

Incoming requests, sending a response back, and exceptions will be logged to the `service_name` logger with these.
Anything else should be logged by the app.

Example usage:
```python3
    from flask import Flask

    app = Flask()

    app.before_request(before_request('SERVICE_NAME', excluded_routes=['/'], excluded_routes_partial=['/config/']))
    app.after_request(after_request('SERVICE_NAME', excluded_routes=['/'], excluded_routes_partial=['/config/']))
    app.teardown_request(teardown_request('SERVICE_NAME'))

```