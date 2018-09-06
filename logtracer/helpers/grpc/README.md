# gRPC Helpers

>These are utilities designed to make integration with a gRPC app simpler.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../../../README.md).
Example code exists in `/examples`, look at these for working implementations.
Once implemented, inbound requests will be logged on opening and closing of the connection and the tracing information will be sent to the Stackdriver Trace API (if desired).
Exceptions tracebacks and responses will be logged too so avoid using `logger.exception(e)` in your gRPC error handlers as this should be handled by this library.

### Tracing Inbound Requests
```python
# app/trace.py
from app.log import logger_factory
from logtracer.helpers.grpc.tracer import GRPCTracer

grpc_tracer = GRPCTracer(
    logger_factory,
    post_spans_to_stackdriver_api=False,
    redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1']
)
grpc_tracer.set_logging_level('DEBUG')
```

```python
import grpc
import time

from app.trace import grpc_tracer
from app.log import logger_factory
from concurrent import futures
from examples.grpc.resources import grpc_demo_pb2_grpc

ONE_DAY_IN_SECONDS = 60 * 60 * 24
grpc_port = 50055


logger = logger_factory.get_logger(__name__)

def create_server(gprc_port):
    #### key part #####
    server_interceptor = grpc_tracer.server_interceptor()
    server = grpc.server(
        futures.ThreadPoolExecutor(),
        interceptors=(server_interceptor,)
    )
    ###################
    grpc_demo_pb2_grpc.add_DemoServiceServicer_to_server(DemoRPC(), server)
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f'Starting gRPC server on http://localhost:{grpc_port}.')
    return server
    

def run_grpc_server():
    server = create_server(grpc_port)
    try:
        while True:
            time.sleep(ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
```

### Tracing Outbound Requests
#### HTTP

```python
from app.trace import grpc_tracer

...

grpc_tracer.requests.get('http://example-get.com')
grpc_tracer.requests.post('http://example-post.com', data={'data':'test'})

...
```


#### HTTP (to a service without `logtracer`)

```python
from app.trace import grpc_tracer

...

grpc_tracer.unsupported_requests.get('http://example-get.com')
grpc_tracer.unsupported_requests.post('http://example-post.com', data={'data':'test'})

...
```


#### gRPC
```python
import grpc
from app.trace import grpc_tracer

grpc_port = 50055

channel = grpc.insecure_channel(f'localhost:{grpc_port}')
intercept_channel = grpc.intercept_channel(channel, grpc_tracer.client_interceptor())
stub = DemoServiceStub(intercept_channel)

message = EmptyMessage()
stub.DemoRPC(message)
```

#### Other
To trace anything else, use the `SubSpanContext`.
```python
from app.trace import grpc_tracer
from app.log import logger_factory
from logtracer.tracing import SubSpanContext

...

logger = logger_factory.get_logger(__name__)

logger.info('Outside of a subspan')
with SubSpanContext(grpc_tracer, 'example-span'):
    logger.info('In a subspan, trace a function or anything else here.')

```
