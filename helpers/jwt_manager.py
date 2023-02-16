import datetime

from flask_jwt_extended import JWTManager

TOKEN_ACCESS_EXPIRES = datetime.timedelta(hours=5)

jwt = JWTManager()
