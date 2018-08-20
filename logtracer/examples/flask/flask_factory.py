from flask import Flask


def build_app(flask_tracer):
    app = Flask('demoFlaskApp')

    app.before_request(flask_tracer.start_span_and_log_request_before())
    app.after_request(flask_tracer.log_response_after())
    app.teardown_request(
        flask_tracer.close_span_and_post_on_teardown(
            excluded_routes=['/exclude-full'],
            excluded_partial_routes=['/exclude-with-path-var']
        )
    )
    return app
