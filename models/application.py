from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from sqlalchemy import Enum
import enum

from models.contract import ContractModel
from typing import List

from models.week import WeekModel


class ApplicationType(enum.Enum):
    FULL = 0
    DAIRY = 1
    FRUIT_VEG = 2


application_contract = db.Table('application_contract',
                                db.Column('application_id', db.Integer, db.ForeignKey('application.id')),
                                db.Column('contract_id', db.Integer, db.ForeignKey('contract.id')))
application_week = db.Table('application_week',
                            db.Column('application_id', db.Integer, db.ForeignKey('application.id')),
                            db.Column('week_id', db.Integer, db.ForeignKey('week.id')))


class ApplicationModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'application'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    no = db.Column(db.Integer, nullable=False)
    type = db.Column(Enum(ApplicationType), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel',
                              backref=db.backref('applications', lazy=True))
    applications = db.relationship('ContractModel', secondary=application_contract, backref='applications')
    weeks = db.relationship('WeekModel', secondary=application_week, backref='applications')

    def __init__(self, program_id, contracts: List[ContractModel], weeks: List[WeekModel],
                 app_type: ApplicationType):
        ApplicationModel.validate_type(program_id, app_type)
        self.no = ApplicationModel.get_next_no(program_id)
        self.program_id = program_id
        self.type = app_type
        self.applications = contracts
        self.weeks = weeks
        self.save_to_db()

    def __str__(self):
        return "{0}/{1}/{2}".format(self.program.semester_no, self.no, self.program.school_year)

    @staticmethod
    def possible_types(program_id):
        prev_app = ApplicationModel.all_filtered_by_program(program_id)
        if prev_app.count() == 0:
            return [ApplicationType.FULL, ApplicationType.DAIRY, ApplicationType.FRUIT_VEG]
        if ApplicationType.FULL in (app.type for app in prev_app):
            return [ApplicationType.FULL]
        return [ApplicationType.DAIRY, ApplicationType.FRUIT_VEG]

    @staticmethod
    def validate_type(program_id, app_type):
        if app_type not in ApplicationModel.possible_types(program_id):
            raise ValueError("Cannot mix full and partial applications in one program")

    @staticmethod
    def get_next_no(program_id):
        return ApplicationModel.all_filtered_by_program(program_id).count() + 1
