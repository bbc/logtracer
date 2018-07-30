import grpc
import requests
from flask import Flask, jsonify, make_response

from examples.grpc.grpc_resources.grpc_demo_pb2 import DemoMessage
from examples.grpc.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc.server import grpc_port
from logtracer.helpers.flask.decorators import trace_and_log_route, trace_and_log_exception
from logtracer.jsonlog import get_logger
from logtracer.tracing import generate_new_traced_subspan_values

# flask
app = Flask('demoFlaskLoggerDecorators')
flask_decorators_port = 5010

# logging
logger = get_logger()
logger.setLevel('DEBUG')

# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


# flask endpoints
@app.route('/', methods=['GET'])
@trace_and_log_route
def index():
    return jsonify({}), 200


@app.route('/grpc', methods=['GET'])
@trace_and_log_route
def grpc():
    message = DemoMessage(
        b3_values=generate_new_traced_subspan_values()
    )
    stub.DemoRPC(message)
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
@trace_and_log_route
def doublehttp():
    requests.get(f'http://localhost:{flask_decorators_port}', headers=generate_new_traced_subspan_values())
    return jsonify({}), 200


@app.route('/exclude', methods=['GET'])
def exclude():
    return jsonify({}), 200


class HandledException(Exception):
    pass


class UnhandledException(Exception):
    pass


@app.route('/handledexception', methods=['GET'])
@trace_and_log_route
def handled_exception():
    raise HandledException('This is a handled Exception!')


@app.route('/unhandledexception', methods=['GET'])
@trace_and_log_route
def unhandled_exception():
    raise UnhandledException('This is an unhandled Exception!')


@app.errorhandler(HandledException)
@trace_and_log_exception
def exception_handler(e):
    return make_response(jsonify(str(e)), 500)


# server
def run_flask_server_decorators():
    logger.info(f'Starting flask server on http://localhost:{flask_decorators_port}.')
    app.run(host='0.0.0.0', port=flask_decorators_port, debug=False, threaded=True)