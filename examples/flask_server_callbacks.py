import grpc
import requests
from flask import Flask, jsonify, make_response

from examples.grpc_resources.grpc_demo_pb2 import EmptyMessage
from examples.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc_server import grpc_port
from stackdriver_logging.flask_helpers.callbacks import before_request, after_request, teardown_request
from stackdriver_logging.flask_helpers.decorators import log_exception
from stackdriver_logging.jsonlog import get_logger
from stackdriver_logging.tracing import generate_traced_subspan_values

# flask
app = Flask('demoFlaskLoggerCallbacks')
flask_callbacks_port = 5005

# logging
logger = get_logger()
logger.setLevel('DEBUG')

# functions to run before and after a request is made
exclude = {
    'excluded_routes': ['/excludefull'],
    'excluded_routes_partial': ['/excludepa']
}
app.before_request(before_request(**exclude))
app.after_request(after_request(**exclude))
app.teardown_request(teardown_request(**exclude))
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
        b3_values=generate_traced_subspan_values()
    )
    stub.DemoRPC(message)
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
def doublehttp():
    requests.get(f'http://localhost:{flask_callbacks_port}', headers=generate_traced_subspan_values())
    return jsonify({}), 200


@app.route('/excludefull', methods=['GET'])
def exclude_full():
    return jsonify({}), 200


@app.route('/excludepartial', methods=['GET'])
def exclude_partial():
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
def run_flask_server_callbacks():
    logger.info(f'Starting flask server on http://localhost:{flask_callbacks_port}.')
    app.run(host='0.0.0.0', port=flask_callbacks_port, debug=False, threaded=True)
