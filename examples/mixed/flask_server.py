import grpc
from flask import jsonify

from examples.flask.flask_factory import build_app
from examples.grpc.resources.grpc_demo_pb2 import EmptyMessage
from examples.grpc.resources.grpc_demo_pb2_grpc import DemoServiceStub
from examples.grpc.server import grpc_port
from examples.mixed.log import logger_factory
from examples.mixed.trace import mixed_tracer

app = build_app(mixed_tracer, post_spans_to_stackdriver_api=False)
flask_port = 5005

logger = logger_factory.get_logger(__name__)
logger.setLevel('DEBUG')

channel = grpc.insecure_channel(f'localhost:{grpc_port}')
intercept_channel = grpc.intercept_channel(channel, mixed_tracer.client_interceptor())
stub = DemoServiceStub(intercept_channel)


@app.route('/grpc', methods=['GET'])
def index():
    message = EmptyMessage()
    stub.DemoRPC(message)
    return jsonify({}), 200


# server
def run_flask_server():
    logger.info(f'Starting flask server on http://localhost:{flask_port}.')
    app.run(host='0.0.0.0', port=flask_port, debug=False, threaded=True)


if __name__ == '__main__':
    run_flask_server()
