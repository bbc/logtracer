# Flask Helpers

>These are utilities designed to make integration with a Flask app simpler. Flask isn't included as a requirement of this
package but it should be in the app you are using this for.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../../../README.md).
Example code exists in `/examples`, look at these for working implementations.
Once implemented, inbound requests will be logged on opening and closing of the connection and the tracing information will be sent to the Stackdriver Trace API (if desired).
Exceptions tracebacks and responses will be logged too so avoid using `logger.exception(e)` in your Flask error handlers as this should be handled by this library.

### Tracing Inbound Requests
Flask has [callbacks](http://flask.pocoo.org/docs/1.0/api/#flask.Flask.after_request) that allow you to run code before and after each request. 
These callbacks can be used to start and end spans and log the requests.

```python
from flask import Flask
from logtracer.helpers.flask.callbacks import start_span_and_log_request_before, log_response_after, close_span_on_teardown 

app = Flask('demoFlaskApp')


exclude = {
    'excluded_routes': ['/excludefull'],
    'excluded_routes_partial': ['/excludepart']
}
app.before_request(start_span_and_log_request_before())
app.after_request(log_response_after())
app.teardown_request(close_span_on_teardown(**exclude))

...
```
If you wish to exclude traces from certain endpoints being posted to the Trace API, then you can either exclude the full 
route using the `excluded_routes` parameter, or exclude a partial route using the `excluded_routes_partial` - this is useful for routes with path variables.

To properly log exception tracebacks, the `log_exception` decorator must be added to any of your implemented Flask error handlers.
```python
from logtracer.helpers.flask.decorators import log_exception
from flask import make_response, jsonify

...

@app.errorhandler(Exception)
@log_exception
def exception_handler(e):
    return make_response(jsonify(str(e)), 500)
    
...
```

### Managing Subspans
When making a call to a downstream service, a values for the subspan must be created. Previous versions of this package
implemented a context manager, this version removes that functionality to keep things as simple as possible to implement - 
it may come back in a later version.

When making an outbound HTTP request to another service implementing this library, the tracing values should be sent in the header. 
This is as simple as
```python
from logtracer.tracing import generate_new_traced_subspan_values
import requests

...

response = requests.get('http://madeupurl.com/endpoint-with-stackdriver-logging', headers=generate_new_traced_subspan_values())

...

```
Similarly, when calling a downstream gRPC service, the code should look similar to the following
```python
from examples.grpc.resources.grpc_demo_pb2 import EmptyMessage
from examples.grpc.resources.grpc_demo_pb2_grpc import DemoServiceStub
from logtracer.tracing import generate_new_traced_subspan_values
import grpc 

channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)

...

message = EmptyMessage(
    b3_values=generate_new_traced_subspan_values()
)
stub.DemoRPC(message)

...
```
I.e. the B3 values should be included in the message. In the `proto` spec, this message looks like
```proto
message EmptyMessage {
    map<string,string> b3_values = <N>;
}
```
where `<N>` is the number of the field.
