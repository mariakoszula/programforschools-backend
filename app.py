import os

from flask import Flask
from flask_jwt import JWT, jwt_required
from flask_restful import Api

from resources.user import UserResource
from security import authenticate, identity

from configparser import ConfigParser, ExtendedInterpolation
from os import path, getcwd, mkdir

config_parser = ConfigParser(interpolation=ExtendedInterpolation())
config_file = path.join(getcwd(), "config.ini")
config_parser.read_file(open(config_file, encoding='utf-8'))

if not path.exists(config_parser.get('Common', 'gen_dir')):
    mkdir(config_parser.get('Common', 'gen_dir'))

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
database_name = f"{config_parser.get('Database', 'type')}://{config_parser.get('Database', 'url')}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', database_name)

app.secret_key = f"{config_parser.get('Common', 'secret_key')}"

api = Api(app)

jwt = JWT(app, authenticate, identity)

api.add_resource(UserResource, '/register')


@app.route("/")
@jwt_required()
def home():
    return f"You've entered home page"


if __name__ == '__main__':
    from db import db
    db.init_app(app)
    app.run(debug=bool(config_parser.get('Common', 'debug_on')), host="0.0.0.0")
