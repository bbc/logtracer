"""Variables to be used across tracing and logging."""
# set by jsonlog.configure_json_logging
gcp_project_name = ''
service_name = ''

# set by tracing.configure_tracing
post_spans_to_stackdriver_api = False