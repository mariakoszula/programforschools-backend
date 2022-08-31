from flask_restful import Resource, reqparse
from models.user import UserModel, Role, AllowedRoles
from flask_jwt_extended import create_access_token, create_refresh_token, \
    jwt_required, get_jwt, get_jwt_identity
from accesscontrol import roles_required, handle_exception_pretty
import copy

_user_parser = reqparse.RequestParser()
_user_parser.add_argument('email',
                          required=True,
                          type=str,
                          help="Email cannot be blank")
_user_parser.add_argument('password',
                          required=True,
                          type=str,
                          help="Password cannot be blank")


class UserResource(Resource):
    parser = copy.deepcopy(_user_parser)
    parser.add_argument('username',
                        required=True,
                        type=str,
                        help="Username cannot be blank")
    parser.add_argument('role',
                        required=False,
                        type=str,
                        default="Admin")

    @classmethod
    def post(cls):
        data = cls.parser.parse_args()
        if UserModel.find_by_email(data['email']):
            return {'message': 'User already exists'}, 400
        try:
            role = Role.find(data['role'])
            if not role:
                role = Role(data['role'])
                role.save_to_db()
            user = UserModel(**data)
            user.save_to_db()
        except Exception as e:
            return {'message': f'User not saved due to {e}'}, 500
        return {'message': f'Added {user.email} to database'}, 201


class User(Resource):
    @classmethod
    @jwt_required()
    def get(cls, user_id):
        user: UserModel = UserModel.find_by_id(user_id)
        if not user:
            return {'message': 'User does not exists'}, 404
        return user.json()

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name])
    def delete(cls, user_id):
        user: UserModel = UserModel.find_by_id(user_id)
        if not user:
            return {'message': 'User does not exists'}, 404
        user.delete_from_db()
        return {'message': 'User deleted'}, 200


class UserLogin(Resource):
    @classmethod
    def post(cls):
        data = _user_parser.parse_args()
        user: UserModel = UserModel.find_by_email(data['email'])
        if user and user.validate_password(data['password']):
            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(user.id)
            return {
                       'id': user.id,
                       'access_token': access_token,
                       'refresh_token': refresh_token
                   }, 200
        return {'message': 'Invalid credentials'}, 401


class RefreshToken(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user_identity = get_jwt_identity()
        new_token = create_access_token(identity=current_user_identity, fresh=False)
        return {'access_token': new_token}, 200


class UserLogout(Resource):
    BLACKLIST = set()  # TODO Change this to using redis database https://flask-jwt-extended.readthedocs.io/en/stable/blocklist_and_token_revoking/

    @classmethod
    @jwt_required(verify_type=False)
    def delete(cls):
        token = get_jwt()
        token_type = token["type"]
        UserLogout.BLACKLIST.add(token["jti"])
        return {'message': f'User logged out, {token_type.capitalize()} token revoked'}, 401


class Users(Resource):
    @classmethod
    @roles_required([AllowedRoles.admin.name])
    def get(cls):
        users: UserModel = UserModel.all()
        if not users:
            return {'message': 'No users found'}, 200
        return {'users': [user.id for user in users]}, 200
