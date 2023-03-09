import sqlalchemy
from helpers.config_parser import config_parser
from os import environ

_host = environ.get('DB_HOST', config_parser.get("Database", "host"))
database_url = config_parser.get("Database", "local_prefix") + _host
engine = sqlalchemy.create_engine(database_url)
