from os import environ
from helpers.config_parser import config_parser
from flask import Flask
from helpers.jwt_manager import TOKEN_ACCESS_EXPIRES, jwt


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = TOKEN_ACCESS_EXPIRES
    db_local_prefix = config_parser.get('Database', 'local_prefix')
    db_remote_prefix = config_parser.get('Database', 'remote_prefix')
    local_db_name = f"{db_local_prefix}{config_parser.get('Database', 'url')}"
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL', local_db_name)
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(db_remote_prefix,
                                                                                          db_local_prefix)
    if secret := environ.get("SECRET_KEY", None):
        app.secret_key = secret
    else:
        app.secret_key = f"{config_parser.get('Common', 'secret_key')}"
    app.config["JWT_SECRET_KEY"] = app.secret_key
    with app.app_context():
        from helpers.db import db

        @app.before_first_request
        def create_tables():
            db.create_all()

        db.init_app(app)
        jwt.init_app(app)
        from routes import create_routes
        create_routes(app)
    return app
