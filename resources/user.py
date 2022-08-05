from flask_restful import Resource, reqparse
from models.user import UserModel


class UserResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', required=True, type=str, help="Username cannot be blank")
    parser.add_argument('password', required=True, type=str, help="Password cannot be blank")
    parser.add_argument('email', required=True, type=str, help="Email cannot be blank")

    def post(self):
        data = UserResource.parser.parse_args()
        if UserModel.find(data['username']):
            return {'message': 'User already exists'}, 400
        try:
            user = UserModel(**data)
            user.save_to_db()
        except Exception as e:
            return {'message': f'User not saved due to {e}'}, 500
        return {'message': f'Added {user.username} to database'}, 201
