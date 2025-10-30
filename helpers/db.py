from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker

scoped_session_factory = scoped_session(sessionmaker(expire_on_commit=False))
db = SQLAlchemy(session_options={'expire_on_commit': False})
