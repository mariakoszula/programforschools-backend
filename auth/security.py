from models.user import UserModel


def authenticate(username, password):
    user: UserModel = UserModel.find(username)
    if user and user.validate_password(password):
        return user


def identity(payload):
    return UserModel.find_by_id(payload['identity'])
