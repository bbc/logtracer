import grpc
import requests
from flask import Flask, jsonify, make_response

from examples.grpc.resources.grpc_demo_pb2 import EmptyMessage
from examples.grpc.resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc.server import grpc_port
from logtracer.helpers.flask.callbacks import start_span_and_log_request_before, log_response_after, \
    close_span_and_post_on_teardown
from logtracer.helpers.flask.decorators import log_exception
from logtracer.jsonlog import get_logger
from logtracer.tracing import generate_new_traced_subspan_values

# flask
app = Flask('demoFlaskApp')
flask_port = 5005

# logging
logger = get_logger()
logger.setLevel('DEBUG')

# functions to run before and after a request is made
app.before_request(start_span_and_log_request_before())
app.after_request(log_response_after())
app.teardown_request(close_span_and_post_on_teardown(
    excluded_routes=['/exclude-full'],
    excluded_partial_routes=['/exclude-with-path-var'])
)
#
# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


# flask endpoints
@app.route('/', methods=['GET'])
def index():
    return jsonify({}), 200


@app.route('/grpc', methods=['GET'])
def grpc():
    message = EmptyMessage(
        b3_values=generate_new_traced_subspan_values()
    )
    stub.DemoRPC(message)
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
def doublehttp():
    requests.get(f'http://localhost:{flask_port}', headers=generate_new_traced_subspan_values())
    return jsonify({}), 200


@app.route('/exclude-full', methods=['GET'])
def exclude_full():
    return jsonify({}), 200


@app.route('/exclude-with-path-var/<example_path_var>', methods=['GET'])
def exclude_partial(example_path_var):
    logger.info(f'Example path variable: {example_path_var}')
    return jsonify({}), 200


class HandledException(Exception):
    pass


class UnhandledException(Exception):
    pass


@app.route('/handledexception', methods=['GET'])
def handled_exception():
    raise HandledException('This is a handled Exception!')


@app.route('/unhandledexception', methods=['GET'])
def unhandled_exception():
    raise UnhandledException('This is an unhandled Exception!')


@app.errorhandler(HandledException)
@log_exception
def exception_handler(e):
    return make_response(jsonify(str(e)), 500)


# server
def run_flask_server():
    logger.info(f'Starting flask server on http://localhost:{flask_port}.')
    app.run(host='0.0.0.0', port=flask_port, debug=False, threaded=True)
