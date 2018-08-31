from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

if __name__ == "__main__":
    setup(
        name="logtracer",
        version="0.3",
        author="Datalab",
        author_email="datalab@bbc.co.uk",
        description="Adds distributed tracing information to logger output and sends traces to the Stackdriver "
                    "Trace API.",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/bbc/logtracer",
        packages=['logtracer', 'logtracer.helpers', 'logtracer.helpers.flask', 'logtracer.helpers.grpc',
                  'logtracer.helpers.mixed', 'logtracer.examples', 'logtracer.examples.grpc',
                  'logtracer.examples.flask', 'logtracer.examples.mixed'],
        classifiers=[
            "Programming Language :: Python :: 3.6",
            "Operating System :: OS Independent",
        ],
        install_requires=[
            'python-json-logger==0.1.9',
            'google-cloud-trace==0.19.0',
            'requests==2.19.1'
        ],
        test_suite="tests",
        setup_requires=[
            'wheel'
        ],
        tests_require=[
            'pytest',
            'pytest-runner',
            'flake8',
            'pytest-cov', ],
    )
