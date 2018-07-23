from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

if __name__ == "__main__":
    setup(
        name="stackdriver_logging",
        version="0.1.3b",
        author="Datalab",
        author_email="datalab@bbc.co.uk",
        description="Adds distributed tracing information to logger output and sends traces to the Stackdriver "
                    "Trace API.",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/bbc/stackdriver_logging",
        packages=find_packages(),
        classifiers=(
            "Programming Language :: Python :: 3.6",
            "Operating System :: OS Independent",
        ),
        install_requires=[
            'python-json-logger==0.1.9',
            'google-cloud-trace==0.19.0',
            'protobuf==3.6.0'
        ]
    )
