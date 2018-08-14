# FlaskTracer
>These are utilities designed to make integration with a Flask app simpler. Flask isn't included as a requirement of this
package but it should be in the app you are using this for.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../../../README.md).
Example code exists in `/examples`, look at these for working implementations.
Once implemented, inbound requests will be logged on opening and closing of the connection, and the tracing information will be sent to the Stackdriver Trace API (if desired).
Exceptions, tracebacks, and responses will be logged too so avoid using `logger.exception(e)` in your Flask error handlers as this should be handled by this library.


### Tracing Inbound Requests
Flask has [callbacks](http://flask.pocoo.org/docs/1.0/api/#flask.Flask.after_request) that allow you to run code before and after each request. 
These callbacks can are used to start and end spans and log the requests.

First, a `FlaskTracer` instance is must be instantiated.

```python
# app/trace.py
from app.log import logger_factory
from logtracer.helpers.flask.tracer import FlaskTracer

...

enable_trace_posting = os.getenv('ENABLE_TRACE_POSTING', 'false') == 'true'
flask_tracer = FlaskTracer(logger_factory, post_spans_to_stackdriver_api=enable_trace_posting)
flask_tracer.set_logging_level('DEBUG') # 'INFO' recommended in production
``` 
Add callbacks in your Flask app:
```python
# app/flask_factory.py
from flask import Flask

from app.trace import flask_tracer

def build_app():
    app = Flask('demoFlaskApp')
    
    app.before_request(flask_tracer.start_span_and_log_request_before())
    app.after_request(flask_tracer.log_response_after())
    app.teardown_request(
        flask_tracer.close_span_and_post_on_teardown(
            excluded_routes=['/exclude-full'],
            excluded_partial_routes=['/exclude-with-path-var']
        )
    )
    return app
```

If you wish to exclude traces from certain endpoints being posted to the Trace API, then you can either exclude the full 
route using the `excluded_routes` parameter, or exclude a partial route using the `excluded_routes_partial` - this is useful for routes with path variables.

To properly log exception tracebacks, the `log_exception` decorator must be added to any of your implemented Flask error handlers.
```python
from app.trace import flask_tracer
from app.flask_factory import build_app

from flask import make_response, jsonify

app = build_app()

...

@app.errorhandler(Exception)
@flask_tracer.log_exception
def exception_handler(e):
    return make_response(jsonify(str(e)), 500)
    
```

### Tracing Outbound Requests

#### HTTP
To trace outbound HTTP requests, use the wrapped `requests` library included with the tracer:

```python
from app.trace import flask_tracer

...

flask_tracer.requests.get('http://example-get.com')
flask_tracer.requests.post('http://example-post.com', data={'data':'test'})

...
```

#### GRPC
To trace an outgoing gRPC request, use the [Mixed Tracer](../mixed) class instead.