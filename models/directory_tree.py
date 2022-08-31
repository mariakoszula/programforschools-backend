from helpers.db import db
from models.base_database_query import BaseDatabaseQuery


class DirectoryTreeModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'directorytree'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(80), nullable=False)
    google_id = db.Column(db.String(44), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('directorytree.id'), nullable=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)

    program = db.relationship('ProgramModel', backref=db.backref('directorytree', lazy=True))
    program = db.relationship('DirectoryTreeModel')
    db.UniqueConstraint('name', 'program_id', 'parent_id')

    def __init__(self, name, google_id, program_id, parent_id=None):
        self.name = name
        self.google_id = google_id
        self.program_id = program_id
        self.parent_id = parent_id

    @classmethod
    def find_by_google_id(cls, google_id):
        return cls.query.filter_by(google_id=google_id).one()

    def json(self):
        data: {} = super().json()
        if not data.get("parent_id", ""):
            del data["parent_id"]
        return data

    def __repr__(self):
        return f"{self.name}: google_id={self.google_id} program_id={self.program_id} parent_id={self.parent_id if self.parent_id else 'empty'}"
