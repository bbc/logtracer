import logging

from examples.mixed.log import logger_factory
from examples.mixed.flask_server import flask_port
from examples.mixed.trace import mixed_tracer

logger = logger_factory.get_logger(__name__)
logger.setLevel('DEBUG')

logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('b3').setLevel(logging.WARNING)


# These demos illustrate simple calls to a Flask and gRPC server as well as a call from a Flask server to a gRPC
# server.
def run_flask_examples():
    # Call a Flask endpoint that calls a gRPC endpoint
    logger.info('Call to Flask grpc endpoint...')
    mixed_tracer.requests.get(f'http://localhost:{flask_port}/grpc')


if __name__ == '__main__':
    mixed_tracer.start_traced_span({}, 'run_examples')

    run_flask_examples()

    mixed_tracer.end_traced_span(exclude_from_posting=False)
