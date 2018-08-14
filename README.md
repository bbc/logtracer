# Log Tracer
> Adds distributed tracing information to logger output and sends traces to the Stackdriver Trace API.

## Examples
Examples for a Flask and a gRPC service exist in the [examples](examples) directory.

TODO: running instructions

## Usage
### Pre Setup
Install: `pip install git+https://github.com/bbc/logtracer@[BRANCH or COMMIT_HASH or TAG_NAME]`.
It is good practise to pin the version or your code may break if this package is updated.


NOTE ABOUT CYCLIC IMPORTING - use separate file

### JSON Logging 
Before any logs are written, a `JSONLoggingFactory` instance must be created. This is used to manage logging, with
optional tracing, across the package.

```python
# app/log.py
from logtracer.jsonlog import JSONLoggerFactory
import os 

project_name = 'bbc-connected-data'
service_name = 'demoApp'

logging_format = os.getenv('LOGGING_FORMAT', 'local')

logger_factory = JSONLoggerFactory(project_name, service_name, logging_format)
logger = logger_factory.get_logger(__name__)
logger.setLevel('DEBUG')
```
Initialise this, as above, _once_ in your app. You may need to initialise it in a separate file to prevent cyclic import errors.
Eg. the above could be contained in `log.py` and across your app you can use:
```python
from app.log import logger_factory

logger = logger_factory.get_logger(__name__)
```

### JSON Logging in Stackdriver Format
To format the JSON logs in such a way that Stackdriver Logs can understand, pass in `stackdriver` as the `logging_format`.
it is recommended you do this using an environmental variable as above.

### Tracing 
By default tracing functionality is disabled, you may use the logging functionality without any tracing functionality.

There are three ways to implement tracing, depending on your use case:
#### `Tracer` class
Use this if you are not using Flask or gRPC, or if you would like to use the library for purposes other than to trace individual requests.
Initialise the Tracer class _once_ in your app, and it is recommended you do it in a seprarate file to avoid cyclic import errors.
```python
# app/trace.py
from app.log import logger_factory
from logtracer.tracing import Tracer

...

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

tracer.start_traced_span(headers, 'example-path')

logger.info('Make traced request in span')
tracer.requests.get('http://example-url.com')

tracer.start_traced_subspan('example-sub-path')

logger.info('Make traced request in subspan')
tracer.requests.get('http://example-url2.com')

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
with SpanContext(tracer, headers, 'example-path'):

    logger.info('Make traced request in span')
    tracer.requests.get('http://example-url.com')
    
    with SubSpanContext(tracer, 'example-sub-path'):
        logger.info('Make traced request in subspan')
        tracer.requests.get('http://example-url2.com')

```
The `Tracer` class (and therefore the `FlaskTracer` and `GRPCTracer` class) has a `requests` property. This wraps the standard
requests library to automatically inject the span values into any outgoing `get`, `post`, `update`, etc. requests.


Both the `FlaskTracer` and `GRPCTracer` class inherit from the `Tracer` class and wrap these features to make implementation simpler.
    
#### `FlaskTracer` class
See readme

#### `GRPCTracer` class
See readme

#### Stackdriver Trace API


### Tracing

TODO: rewrite this

By default tracing functionality is disabled - tracing IDs will not show in the logs and nothing will be posted to the Stackdriver Trace API.
There are three steps to enabling tracing:
#### 1. Configure Tracing
Configure it as follows (using an environmental variable), making sure to do this before writing any logs. It is advised to leave it disabled when working locally.
```python
from logtracer.tracing import configure_tracing
import os 

configure_tracing(post_spans_to_stackdriver_api=enable_trace_posting)
```
If you choose to enable posting trace information to the API  _locally_ (unadvised unless you are specifically testing functionality of the Trace API), 
then you *must* set up authentication for the [google-cloud-trace](https://pypi.org/project/google-cloud-trace/) client using the following command: 
```
gcloud auth application-default login
```
If `post_spans_to_stackdriver_api` is set to `True`, and GCP Credentials are not found, an exception will be raised.

If you deploying to a Kubernetes container, then it should automatically pick up the GCP credentials. 

#### 2. Create Spans



Running `configure_tracing` alone will _not_ show any tracing information. To add traces, requests must be handled inside a span.
Any log entries written inside a span will have the span's `trace id` and `span id` attached. 
```python
from logtracer.tracing import start_traced_span, end_traced_span

...

logger.info('log entry without trace info')
start_traced_span(inbound_headers, request_path)

...

logger.info('log entry with trace info')

...

end_traced_span()
logger.info('log entry without trace info')
```

If you are using Flask or gRPC, then there are helpers available to simplify implementation:
- [Implementing Tracing in a Flask App](logtracer/helpers/flask)
- [Implementing Tracing in a gRPC App](logtracer/helpers/grpc)

#### 3. Send Trace Information to Downstream Services
When making a call to a downstream service, values for the subspan must be created. Previous versions of this package
implemented a context manager, this version removes that functionality to keep things as simple as possible to implement - 
it may come back in a later version.

When making an outbound HTTP request to another service implementing this library, the tracing values should be sent in the header. 
This is as simple as
```python
from logtracer.tracing import generate_new_traced_subspan_values
import requests

...
# must be inside a span
response = requests.get('http://example-downstream-http-microservice.com/endpoint', headers=generate_new_traced_subspan_values())

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

# must be inside a span
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


## Purpose

Make it simple to generate and propagate tracing metadata between Python microservices and post them to a tracing API.
Package functionality can be separated into two areas, logging and tracing.

### Logging

Using the logging part of this package allows logs to be written in `JSON` format. The logging handler added by this package 
writes the logs in JSON using [python-json-logger](https://github.com/madzak/python-json-logger). Currently two formatters are implemented,
`local` and `stackdriver`. Examples of each:

#### `local`
```
{"severity": "INFO", "time": "2018-07-25T14:06:05.499727", "sourceLocation": {"file": "/Users/windet01/Files/Code/logtracer/logtracer/flask_helpers/decorators.py", "line": 21, "function": "wrapper"}, "message": "demoApp - GET - http://localhost:5010/", "traceId": "854a7fbec6f0c912f6745b514a2ae6ee", "spanID": "231d2786b123764e"}
```
This formatter simply prints the log information to stdout in JSON, with some added fields.

#### `stackdriver`
```
{"severity": "INFO", "time": "2018-07-25T14:06:09.949433", "logging.googleapis.com/sourceLocation": {"file": "/Users/windet01/Files/Code/logtracer/logtracer/flask_helpers/callbacks.py", "line": 17, "function": "execute_before_request"}, "message": "demoApp - GET - http://localhost:5005/", "logging.googleapis.com/trace": "projects/bbc-connected-data/traces/89f78ff01d84e130a43f2461dddb996f", "logging.googleapis.com/spanId": "d259b23ab3d81bdd"}
```
This format prints the information to stdout in JSON, with keys named in a way that [Stackdriver Logs](https://cloud.google.com/logging/) is able to parse them.
The `stackdriver` formatter is useful when working with containers in Google Kubernetes Engine with logging enabled 
[(more info)](https://cloud.google.com/kubernetes-engine/docs/how-to/logging). 

With logging enabled in the Kubernetes cluster, anything written to `stdout`/`stderr` by a container is parsed by a 
[fluentd daemon](https://github.com/GoogleCloudPlatform/fluent-plugin-google-cloud) and sent to the Stackdriver Logs API. 
If the log entries are written in JSON, then the daemon can process [certain fields](https://cloud.google.com/logging/docs/agent/configuration#special_fields_in_structured_payloads) 
in the entry, any fields not recognised are thrown into a `jsonPayload` field. <sup>*</sup> 


### Tracing
Two important pieces of metadata dealt with by this module are the `span id` and the `trace id` (using code adapted from [B3-Propagation](https://github.com/davidcarboni/B3-Propagation)). 
These parameters make it possible to trace requests across different services, an approach described in more detail in the 
[openzipkin/b3-propagation](https://github.com/openzipkin/b3-propagation) repository. 

Currently, these IDs are included in the JSON logs if present and omitted if not. 
The span details are also posted to the [Stackdriver Trace API](https://cloud.google.com/trace/), this functionality is *disabled* by default. 
The Trace API exists separate to the Logging API, meaning that unfortunately the Trace API cannot pull the trace information 
from the logs. Instead, these have to be posted separately. This package does this using Google's [google-cloud-trace](https://pypi.org/project/google-cloud-trace/)
Python client. Calls to this are not of negligible time, so they are made in a new thread to ensure requests are not blocked. Traces can be viewed in the
Trace API and they are linked to the logs by tracing metadata as shown in the image below.

![example trace](examples/example_trace.png)



## Notes
\* Some fields may not be parsed as expected, this is likely due to the version of the 
[fluentd plugin](https://github.com/GoogleCloudPlatform/fluent-plugin-google-cloud) not being the latest. 
For example, the `logging.googleapis.com/span_id` field is only supported in more recent versions of the plugin.
