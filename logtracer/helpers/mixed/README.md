# MixedTracer
>Utility for integration with a Flask app that calls a gRPC app.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../../../README.md).
Example code exists in `/examples`, look at these for working implementations.
Once implemented, inbound requests will be logged on opening and closing of the connection and the tracing information will be sent to the Stackdriver Trace API (if desired).
Exceptions tracebacks and responses will be logged too so avoid using `logger.exception(e)` in your gRPC error handlers as this should be handled by this library.

### Tracing Inbound Requests
Initialise the Mixed tracer as below, 
```python
# app/trace.py
import os

from app.log import logger_factory
from logtracer.helpers.mixed.tracer import MixedTracer

...

enable_trace_posting = os.getenv('ENABLE_TRACE_POSTING', 'false') == 'true'
tracer = MixedTracer(logger_factory, post_spans_to_stackdriver_api=enable_trace_posting)
tracer.set_logging_level('DEBUG') # 'INFO' recommended in production
``` 
Then add callbacks to your Flask app as described [Flask Helpers](../flask).

### Tracing Outbound Requests
#### HTTP
Use the wrapped `requests` library included in the tracer:
```python
from app.trace import tracer

...

tracer.requests.get('http://example-get.com')
tracer.requests.post('http://example-post.com', data={'data':'test'})

...
```

#### gRPC
User the channel interceptor inherited from GRPCTracer:
```python
import grpc
from app.trace import tracer

grpc_port = 50055

channel = grpc.insecure_channel(f'localhost:{grpc_port}')
intercept_channel = grpc.intercept_channel(channel, tracer.client_interceptor())
stub = DemoServiceStub(intercept_channel)

message = EmptyMessage()
stub.DemoRPC(message)
```