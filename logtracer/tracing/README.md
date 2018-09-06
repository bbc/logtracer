# Tracer
>Use the Tracer class if you are _not_ using Flask or gRPC, or if you would like to use the library for purposes other than to trace individual requests.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../README.md).
Example code exists in `/examples`, look at these for working implementations.
Initialise the Tracer class _once_ in your app, and it is recommended you do it in a separate file to avoid cyclic import errors.

```python
# app/trace.py
from app.log import logger_factory
from logtracer.tracing import Tracer

enable_trace_posting = os.getenv('ENABLE_TRACE_POSTING', 'false') == 'true'
tracer = Tracer(logger_factory, post_spans_to_stackdriver_api=enable_trace_posting)
tracer.set_logging_level('DEBUG') # 'INFO' recommended in production
```
Using the Tracer instance to manage spans:
```python
from app.trace.py import tracer
from app.log import logger_factory

logger = logger_factory.get_logger(__name__)

logger.info('Outside of span')

tracer.start_traced_span(headers, 'example-span')
logger.info('In span')

tracer.start_traced_subspan('example-sub-span')
logger.info('In sub span')

tracer.start_traced_subspan('example-sub-sub-span')
logger.info('In sub sub span')

tracer.end_traced_subspan(exclude_from_posting=False)

tracer.end_traced_subspan(exclude_from_posting=False)

tracer.end_traced_span(exclude_from_posting=False)

```
Or, using context managers:

```python
from app.trace.py import tracer
from app.log import logger_factory
from logtracer.tracing import SpanContext, SubSpanContext

...

logger = logger_factory.get_logger(__name__)

logger.info('Outside of span')
with SpanContext(tracer, headers, 'example-span'):
    logger.info('In span')
    with SubSpanContext(tracer, 'example-sub-span'):
        logger.info('In sub span')
        with SubSpanContext(tracer, 'example-sub-sub-span'):
            logger.info('In sub sub span')

```
The `Tracer` class (and therefore the `FlaskTracer`, `GRPCTracer` and `MixedTracer` classes) have a `requests` property. This wraps the standard
requests library to automatically inject the span values into any outgoing `get`, `post`, `update`, etc. requests.


### Tracing Outbound Requests

#### HTTP 
To trace outbound HTTP requests to another service with `logtracer` installed, use the wrapped `requests` library included with the tracer:

```python
from app.trace import tracer

...

tracer.requests.get('http://example-get.com')
tracer.requests.post('http://example-post.com', data={'data':'test'})

...
```

#### HTTP (to a service without `logtracer`)

```python
from app.trace import tracer

...

tracer.unsupported_requests.get('http://example-get.com')
tracer.unsupported_requests.post('http://example-post.com', data={'data':'test'})

...
```

#### GRPC
To trace an outgoing gRPC request, use the [Mixed Tracer](../mixed) or [gRPC Tracer](../grpc) class instead.

#### Other
To trace anything else, use the `SubSpanContext`.
```python
from app.trace import tracer
from app.log import logger_factory
from logtracer.tracing import SubSpanContext

...

logger = logger_factory.get_logger(__name__)

logger.info('Outside of a subspan')
with SubSpanContext(tracer, 'example-span'):
    logger.info('In a subspan, trace a function or anything else here.')

```
