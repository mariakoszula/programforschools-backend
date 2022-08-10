import enum
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt


class AccessControlError(Exception):
    def __init__(self, msg, code):
        self.msg = msg
        self.code = code

    def json(self):
        return {'message': self.msg}, self.code


class AllowedRoles(enum.Enum):
    nobody = 0
    admin = 1
    program_manager = 2
    finance_manager = 3


def roles_required(roles: [AllowedRoles]):
    def wrap(func):
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get('role', AllowedRoles.nobody.name)
            if not any([AllowedRoles[role] == AllowedRoles[_role] for _role in roles]):
                raise AccessControlError(f"'{role}' not authorized for this action", 401)
            return func(*args, **kwargs)
        return wrapper_function
    return wrap


def handle_exception_pretty(func):
    @wraps(func)
    def wrapper_function(*args, **kwargs):
        try:
            output = func(*args, **kwargs)
        except AccessControlError as e:
            return e.json()
        return output
    return wrapper_function
