from helpers.db import db
from models.base_database_query import BaseDatabaseQuery


class CompanyModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    nip = db.Column(db.String(80), unique=True, nullable=False)
    regon = db.Column(db.String(80), unique=True, nullable=False)
    street = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(120), nullable=False)

    def __init__(self, name, nip, regon, street, city, code):
        self.code = code
        self.city = city
        self.street = street
        self.regon = regon
        self.nip = nip
        self.name = name

    @classmethod
    def find_by_nip(cls, nip):
        return cls.query.filter_by(nip=nip).first()
