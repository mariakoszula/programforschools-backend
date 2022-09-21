from helpers.db import db
from models.base_database_query import BaseDatabaseQuery


class SchoolModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'school'

    id = db.Column(db.Integer, primary_key=True)
    nick = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(120))
    address = db.Column(db.String(120), unique=True)
    city = db.Column(db.String(30))
    nip = db.Column(db.String(80))
    regon = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(80), unique=True)
    phone = db.Column(db.String(80))
    responsible_person = db.Column(db.String(60))
    representative = db.Column(db.String(120))
    representative_nip = db.Column(db.String(80))
    representative_regon = db.Column(db.String(80))

    def __repr__(self):
        return f"School: {self.nick}"

    @classmethod
    def find_one_by_nick(cls, nick):
        return cls.query.filter_by(nick=nick).one()
