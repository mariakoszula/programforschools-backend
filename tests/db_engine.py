from sqlalchemy import create_engine

from helpers.config_parser import config_parser

database_url = config_parser.get("Database", "local_prefix") + config_parser.get("Database", "host")
engine = create_engine(database_url,
                       pool_size=10,
                       max_overflow=20,
                       pool_timeout=30,
                       pool_recycle=1800,
                       pool_pre_ping=True,  # test connections before use to avoid errors with stale connections
                       echo=True  # Set True for SQL logging during debugging
)
