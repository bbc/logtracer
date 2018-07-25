# Flask Helpers

These are utilities designed to make integration with a Flask app simpler. Flask isn't included as a requirement of this
package but it should be in the app you are using this for.

## Implementation Guide
Here the steps on how to implement this library in a Flask app will be detailed.
### 1) Credentials
local/kube/other
disabled by default

### 2) Configure 
configure_json_logging

There are two ways you can implement tracing in your Flask app using this package:
## 1) Using Flask Callbacks
Flask has [callbacks](http://flask.pocoo.org/docs/1.0/api/#flask.Flask.after_request) that allow you to run code before and after each request. 

These callbacks can be used to start and end spans.

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

explain why span closed in teardown (so exceptions are caught too)