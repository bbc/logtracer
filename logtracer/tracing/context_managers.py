class SpanContext:
    def __init__(self, tracer, incoming_headers, span_name, exclude_from_posting=False):
        """Context manager for creating a span."""
        self.tracer = tracer
        self.span_name = span_name
        self.exclude = exclude_from_posting
        self.incoming_headers = incoming_headers

    def __enter__(self):
        self.tracer.start_traced_span(self.incoming_headers, self.span_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracer.end_traced_span(self.exclude)


class SubSpanContext:
    def __init__(self, tracer, span_name, exclude_from_posting=False):
        """Context manager for creating a subspan."""
        self.tracer = tracer
        self.span_name = span_name
        self.exclude = exclude_from_posting

    def __enter__(self):
        self.tracer.start_traced_subspan(self.span_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracer.end_traced_subspan(self.exclude)