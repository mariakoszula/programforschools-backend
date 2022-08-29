from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from accesscontrol import AllowedRoles


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Enum(AllowedRoles), unique=True)

    def __init__(self, name):
        self.name: AllowedRoles = name

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find(cls, name):
        return cls.query.filter_by(name=name).first()

    def json(self):
        return self.name.name


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),  unique=True)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(80), unique=True)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role')

    def __init__(self, username, password, email, role):
        role = Role.find(role)
        if not role:
            raise ValueError(f"Role {role} does not exists in Role table")
        self.role_id = role.id
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.email = email

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def users(cls):
        return cls.query.all()

    def json(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.json()
        }
