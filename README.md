# Python GCP Trace Logging [WIP]
> "Adds distributed tracing information to logger output and sends traces to the Stackdriver Trace API."

## Purpose

Make it simple to generate and propagate B3 headers between Python microservices.
The package has three core functions:
1. Add a handler to the `root` logger that writes log entries into `stdout` in JSON, which 
[Stackdriver Logs](https://cloud.google.com/logging/) can parse.

2. Decorate each log entry with a `span id` and a `trace id`.

3. Send spans to the [Stackdriver Trace API](https://cloud.google.com/trace/). 

## Motivation
This setup is useful when working with containers in Google Kubernetes Engine with logging enabled 
[(more info)](https://cloud.google.com/kubernetes-engine/docs/how-to/logging). 

With logging enabled in the K8s cluster, anything written to `stdout`/`stderr` by a container is parsed by a 
[fluentd daemon](https://github.com/GoogleCloudPlatform/fluent-plugin-google-cloud) and sent to the Stackdriver Logs API. 
If the log entries are written in JSON, then the daemon can process certain fields in the entry, as described 
[here](https://cloud.google.com/logging/docs/agent/configuration#special_fields_in_structured_payloads). 
Any fields not recognised are thrown into a `jsonPayload` field. <sup>*</sup> The logging handler added by this package 
writes the logs in JSON using [python-json-logger](https://github.com/madzak/python-json-logger), and adds extra metadata which Stackdriver Logs expects.

Two important pieces of metadata added are the `span id` and the `trace id`. These parameters make it possible to trace 
requests across different services, this approach is described in more detail in the 
[openzipkin/b3-propagation](https://github.com/openzipkin/b3-propagation) repository. David Carboni's
[B3-Propagation](https://github.com/davidcarboni/B3-Propagation) package is used to handle generation of these tracing IDs in this package.

The Stackdriver Trace API separate to logging, uses google python client to send spans in a background thread.

## Usage
see example of flask interacting with grpc 

always start span before log

## Notes
\* Some fields may not be parsed as expected, this is likely due to the version of the 
[fluentd plugin]([fluentd daemon](https://github.com/GoogleCloudPlatform/fluent-plugin-google-cloud)) not being the latest. 
For example, the `logging.googleapis.com/span_id` field is only supported in more recent versions of the plugin.

start before log