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
If handling exceptions with decorators, then the exception-handling decorators should be _above_ the `trace_all_calls` decorator or the `trace_call` decorators.


