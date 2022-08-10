from configparser import ConfigParser, ExtendedInterpolation
from os import path, getcwd, mkdir, environ

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restful import Api

from accesscontrol import roles_required, AllowedRoles
from models.user import UserModel
from resources.user import UserResource, User, UserLogin

config_parser = ConfigParser(interpolation=ExtendedInterpolation())
config_file = path.join(getcwd(), "config.ini")
config_parser.read_file(open(config_file, encoding='utf-8'))

if not path.exists(config_parser.get('Common', 'gen_dir')):
    mkdir(config_parser.get('Common', 'gen_dir'))

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

db_local_prefix = config_parser.get('Database', 'local_prefix')
db_remote_prefix = config_parser.get('Database', 'remote_prefix')
local_db_name = f"{db_local_prefix}{config_parser.get('Database', 'url')}"
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL', local_db_name)
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(db_remote_prefix, db_local_prefix)

app.secret_key = f"{config_parser.get('Common', 'secret_key')}"

api = Api(app)

jwt = JWTManager(app)


@jwt.additional_claims_loader
def add_role_claims_to_access_token(identity):
    user = UserModel.find_by_id(identity)
    if user:
        return {'role': user.role.json()}


api.add_resource(UserResource, '/register')
api.add_resource(User, '/user/<int:user_id>')
api.add_resource(UserLogin, '/login')


@app.route("/")
@roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
def home():
    return {'message': "You've entered home page"}, 200


@app.before_first_request
def create_tables():
    db.create_all()


if __name__ == '__main__':
    from db import db

    db.init_app(app)
    app.run(debug=bool(config_parser.get('Common', 'debug_on')), host="0.0.0.0")
