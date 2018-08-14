from logtracer.jsonlog import JSONLoggerFactory

project_name = 'bbc-connected-data'
service_name = 'demoApp'
logger_factory = JSONLoggerFactory(project_name, service_name, 'stackdriver')
