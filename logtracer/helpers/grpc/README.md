# gRPC Helpers

>These are utilities designed to make integration with a gRPC app simpler.

## Implementation Guide
Before following these instructions, make sure to follow the instructions in the [main readme](../../../README.md).
Example code exists in `/examples`, look at these for working implementations.
Once implemented, inbound requests will be logged on opening and closing of the connection and the tracing information will be sent to the Stackdriver Trace API (if desired).
Exceptions tracebacks and responses will be logged too so avoid using `logger.exception(e)` in your gRPC error handlers as this should be handled by this library.

### Tracing Inbound Requests
You can handle inbound gRPC calls to your app using the decorators provided here. You can choose to either trace all 
calls with the `trace_all_calls` decorator or choose certain methods and decorate them with `trace_call`.

The decorator accepts an argument for `redacted_fields` to be specified, as by default the full inbound request is logged. 
It will replace any matching fields with `"REDACTED"` and ignore if it cant find the field. You may specify nested fields.

```python
from logtracer.helpers.grpc.decorators import trace_all_calls
from examples.grpc.resources import grpc_demo_pb2_grpc, grpc_demo_pb2

@trace_all_calls(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    def DemoRPC(self, request, context):
        return grpc_demo_pb2.EmptyMessage()

```

```python
from logtracer.helpers.grpc.decorators import trace_call
from examples.grpc.resources import grpc_demo_pb2_grpc, grpc_demo_pb2

class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    @trace_call(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
    def DemoRPCRedactedParameters(self, request, context):
        return grpc_demo_pb2.EmptyMessage()

```

If handling exceptions with decorators, then the exception-handling decorators should be _above_ the `trace_all_calls` decorator or the `trace_call` decorators as below:


```python
import grpc
from examples.grpc.resources import grpc_demo_pb2_grpc, grpc_demo_pb2
from logtracer.helpers.grpc.decorators import trace_call, trace_all_calls


#### Exception handlers ####

def handle_exceptions(f):
    def wrapper(self, request, context):
        try:
            return f(self, request, context)
        except Exception:
            context.abort(grpc.StatusCode.INTERNAL, 'Handled exception, closing context')

    return wrapper
    
    
def handle_exception_for_all_methods():
    """Apply a the `handle_exceptions` decorator to all methods of a Class, excluding `__init__`."""

    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr != '__init__':
                setattr(cls, attr, handle_exceptions(getattr(cls, attr)))
        return cls

    return decorate
    
    
#### Exception handling with `trace_call` decorator ####

# correct example
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    @handle_exceptions
    @trace_call(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
    def DemoRPCRedactedParameters(self, request, context):
        return grpc_demo_pb2.EmptyMessage()
        
# incorrect example, the context will be aborted before the tracing decorator can close the span (and therefore post it)
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    @trace_call(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
    @handle_exceptions
    def DemoRPCRedactedParameters(self, request, context):
        return grpc_demo_pb2.EmptyMessage()


#### Exception handling with `trace_all_calls` decorator ####

# correct example
@handle_exception_for_all_methods()
@trace_all_calls(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    def DemoRPC(self, request, context):
        return grpc_demo_pb2.EmptyMessage()
        

# incorrect example, the context will be aborted before the span can be closed
@trace_all_calls(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
@handle_exception_for_all_methods()
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    def DemoRPC(self, request, context):
        return grpc_demo_pb2.EmptyMessage()
        
        
# incorrect example, the context will be aborted before the span can be closed
@trace_all_calls(redacted_fields=['value1', 'nested.nestedvalue1', 'nested.doublenested.doublenestedvalue1'])
class DemoRPC(grpc_demo_pb2_grpc.DemoServiceServicer):
    @handle_exceptions
    def DemoRPC(self, request, context):
        return grpc_demo_pb2.EmptyMessage()

```