from logtracer.jsonlog import JSONLoggerFactory, Formatters

project_name = 'bbc-connected-data'
service_name = 'demoApp'
logger_factory = JSONLoggerFactory(project_name, service_name, Formatters.stackdriver)
