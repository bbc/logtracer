import requests
from flask import jsonify, make_response

from examples.flask.flask_factory import build_app

# flask
app, flask_tracer, logger_handler = build_app()
flask_port = 5005

# logging
logger = logger_handler.get_logger(__name__)
logger.setLevel('DEBUG')


@app.route('/', methods=['GET'])
def index():
    logger.info('Root called')
    return jsonify({}), 200


@app.route('/doublehttp', methods=['GET'])
def doublehttp():
    logger.info('Calling root endpoint...')
    requests.get(f'http://localhost:{flask_port}', headers=flask_tracer.generate_new_traced_subspan_values())
    logger.info('Done')
    return jsonify({}), 200


@app.route('/exclude-full', methods=['GET'])
def exclude_full():
    logger.info('Excluded endpoint called')
    return jsonify({}), 200


@app.route('/exclude-with-path-var/<example_path_var>', methods=['GET'])
def exclude_partial(example_path_var):
    logger.info(f'Excluded endpoint with path variable: {example_path_var}')
    return jsonify({}), 200


class HandledException(Exception):
    pass


class UnhandledException(Exception):
    pass


@app.route('/handledexception', methods=['GET'])
def handled_exception():
    logger.info('Handled exception endpoint called')
    raise HandledException('This is a handled Exception!')


@app.route('/unhandledexception', methods=['GET'])
def unhandled_exception():
    logger.info('Unhandled exception endpoint called')
    raise UnhandledException('This is an unhandled Exception!')


@app.errorhandler(HandledException)
@flask_tracer.log_exception
def exception_handler(e):
    logger.info('Exception handler invoked')
    return make_response(jsonify(str(e)), 500)


# server
def run_flask_server():
    logger.info(f'Starting flask server on http://localhost:{flask_port}.')
    app.run(host='0.0.0.0', port=flask_port, debug=False, threaded=True)


if __name__ == '__main__':
    run_flask_server()
