# Stackdriver Logging
> Adds distributed tracing information to logger output and sends traces to the Stackdriver Trace API.


## Usage
### Pre Setup
Install: `pip install git+https://github.com/bbc/python-gcp-trace-logging@[BRANCH or COMMIT_HASH or TAG_NAME]`.
It is good practise to pin the version or your code may break if this package is updated.

### Logging
Before writing any logs, the `configure_json_logging` command must be ran.
There are two formatters availale for usage with logging, `local` and `stackdriver`, described further in the [Purpose](#purpose) section.
It is advisable to set this using an environmental variable, as below:
```python
from stackdriver_logging.jsonlog import configure_json_logging, get_logger
import os

logging_format = os.getenv('LOGGING_FORMAT', 'local')
configure_json_logging('project name', 'service name', logging_format)
logger = get_logger()
logger.setLevel('INFO')
```


### Tracing
By default tracing functionality is disabled - tracing IDs will not show in the logs and nothing will be posted to the Stackdriver Trace API.
Enable it as follows (using an environmental variable), making sure to do this before writing any logs. It is advised to leave it disabled when working locally.
```python
from stackdriver_logging.tracing import configure_tracing
import os 

enable_trace_posting = os.getenv('ENABLE_TRACE_POSTING', 'false') == 'true'
configure_tracing(post_spans_to_api=enable_trace_posting)
```
If you choose to enable posting trace information to the API  _locally_ (unadvised unless you are specifically testing functionality of the Trace API), 
then you *must* set up authentication for the [google-cloud-trace](https://pypi.org/project/google-cloud-trace/) client using the following command: 
```
gcloud auth application-default login
```

If you are using it in a Kubernetes container, then it should automatically pick up the GCP credentials. 
However, this is not enough to configure tracing - tracing IDs will still not show in logs. To enable tracing functionality, 
requests must be inside a span, follow one of the guides to implement this:
- [Implementing Tracing in a Flask App](stackdriver_logging/helpers/flask)
- [Implementing Tracing in a gRPC App](stackdriver_logging/helpers/grpc)


## Purpose

Make it simple to generate and propagate tracing metadata between Python microservices and post them to a tracing API.
Package functionality can be separated into two areas, logging and tracing.

### Logging

Using the logging part of this package allows logs to be written in `JSON` format. The logging handler added by this package 
writes the logs in JSON using [python-json-logger](https://github.com/madzak/python-json-logger). Currently two formatters are implemented,
`local` and `stackdriver`. Examples of each:

#### `local`
```
{"severity": "INFO", "time": "2018-07-25T14:06:05.499727", "sourceLocation": {"file": "/Users/windet01/Files/Code/stackdriver_logging/stackdriver_logging/flask_helpers/decorators.py", "line": 21, "function": "wrapper"}, "message": "demoApp - GET - http://localhost:5010/", "traceId": "854a7fbec6f0c912f6745b514a2ae6ee", "spanID": "231d2786b123764e"}
```
This formatter simply prints the log information to stdout in JSON, with some added fields.

#### `stackdriver`
```
{"severity": "INFO", "time": "2018-07-25T14:06:09.949433", "logging.googleapis.com/sourceLocation": {"file": "/Users/windet01/Files/Code/stackdriver_logging/stackdriver_logging/flask_helpers/callbacks.py", "line": 17, "function": "execute_before_request"}, "message": "demoApp - GET - http://localhost:5005/", "logging.googleapis.com/trace": "projects/bbc-connected-data/traces/89f78ff01d84e130a43f2461dddb996f", "logging.googleapis.com/spanId": "d259b23ab3d81bdd"}
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
The Trace API exists separate to the Logging API, meaning that unfortunately the Trace API cannot pull the trace IDs 
from the logs. Instead, these have to be posted separately. This package does this using Google's [google-cloud-trace](https://pypi.org/project/google-cloud-trace/)
Python client. Calls to this can be quite slow, so they are made in a new thread to ensure no blocking. Traces can be viewed in the
Trace API and they are linked to the logs by tracing metadata as shown in the image below.

![example trace](examples/example_trace.png)





## Notes
\* Some fields may not be parsed as expected, this is likely due to the version of the 
[fluentd plugin](https://github.com/GoogleCloudPlatform/fluent-plugin-google-cloud) not being the latest. 
For example, the `logging.googleapis.com/span_id` field is only supported in more recent versions of the plugin.
