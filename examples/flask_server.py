import logging
import socket

import grpc
import requests
from flask import Flask, jsonify, request

from examples.grpc_resources.grpc_demo_pb2 import DemoMessage
from examples.grpc_resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc_server import grpc_port
from gcptracelogging.tracing import start_span, end_span, TracedSubSpan

# flask
app = Flask('demoFlaskApp')
flask_port = 5005

# logging
logger = logging.getLogger('demoFlaskLogger')
logger.setLevel('DEBUG')

# for grpc request
channel = grpc.insecure_channel(f'localhost:{grpc_port}')
stub = DemoServiceStub(channel)


# functions to run before and after a request is made
def before():
    start_span(request.headers, 'demoApp', request.path, f'http://localhost:{flask_port}')
    logger.info(f'{request.method} - {request.url}')


def after(response):
    logger.info(f'{response.status} - {request.url}')
    end_span()
    return response


app.before_request(before)
app.after_request(after)


# flask endpoints
@app.route('/', methods=['GET'])
def index():
    return jsonify({}), 200


@app.route('/grpc', methods=['GET'])
def grpc():
    with TracedSubSpan() as b3_headers:
        message = DemoMessage(
            b3_values=b3_headers
        )
        stub.DemoRPC(message)
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
def doublehttp():
    with TracedSubSpan() as b3_headers:
        requests.get(f'http://localhost:{flask_port}', headers=b3_headers)
    return jsonify({})


# server
def run_flask_server():
    logger.info(f'Starting flask server on http://localhost:{flask_port}.')
    app.run(host='0.0.0.0', port=flask_port, debug=False, threaded=True)
