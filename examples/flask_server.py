import logging

import grpc
import requests
from flask import Flask, jsonify

from examples.grpc_resources.grpc_demo_pb2 import DemoMessage
from examples.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc_server import grpc_port
from stackdriver_logging.flask_helpers.callbacks import before_request, after_request, teardown_request
from stackdriver_logging.jsonlog import get_logger
from stackdriver_logging.tracing import generate_traced_subspan_values

# flask
app = Flask('demoFlaskLogger')
flask_port = 5005

# logging
logger = get_logger()
logger.setLevel('DEBUG')

# functions to run before and after a request is made
app.before_request(before_request())
app.after_request(after_request())
app.teardown_request(teardown_request())

# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


# flask endpoints
@app.route('/', methods=['GET'])
def index():
    return jsonify({}), 200


@app.route('/grpc', methods=['GET'])
def grpc():
    message = DemoMessage(
        b3_values=generate_traced_subspan_values()
    )
    stub.DemoRPC(message)
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
def doublehttp():
    requests.get(f'http://localhost:{flask_port}', headers=generate_traced_subspan_values())
    return jsonify({}), 200


# server
def run_flask_server():
    logger.info(f'Starting flask server on http://localhost:{flask_port}.')
    app.run(host='0.0.0.0', port=flask_port, debug=False, threaded=True)
