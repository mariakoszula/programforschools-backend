from sqlalchemy import create_engine

from helpers.config_parser import config_parser

database_url = config_parser.get("Database", "local_prefix") + config_parser.get("Database", "host")
engine = create_engine(database_url)
