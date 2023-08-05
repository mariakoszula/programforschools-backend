from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from sqlalchemy import Enum
import enum
from os import path
from helpers.config_parser import config_parser
from models.contract import ContractModel
from typing import List

from models.product import ProductTypeModel
from models.week import WeekModel


class ApplicationType(enum.Enum):
    FULL = 0
    DAIRY = 1
    FRUIT_VEG = 2

    @staticmethod
    def convert_to_str(name):
        if ApplicationType.FULL == name:
            return f"{ProductTypeModel.DAIRY_TYPE} i {ProductTypeModel.fruit_veg_name()}"
        elif ApplicationType.DAIRY == name:
            return ProductTypeModel.dairy_name()
        elif ApplicationType.FRUIT_VEG == name:
            return ProductTypeModel.fruit_veg_name()


application_contract = db.Table('application_contract',
                                db.Column('application_id', db.Integer, db.ForeignKey('application.id', ondelete='CASCADE')),
                                db.Column('contract_id', db.Integer, db.ForeignKey('contract.id')))
application_week = db.Table('application_week',
                            db.Column('application_id', db.Integer, db.ForeignKey('application.id', ondelete='CASCADE')),
                            db.Column('week_id', db.Integer, db.ForeignKey('week.id')))


class   ApplicationModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'application'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    no = db.Column(db.Integer, nullable=False)
    type = db.Column(Enum(ApplicationType), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel',
                              backref=db.backref('applications', lazy=True))
    contracts = db.relationship('ContractModel', secondary=application_contract, backref='applications')
    weeks = db.relationship('WeekModel', secondary=application_week, backref='applications')

    def __init__(self, program_id, contracts: List[ContractModel], weeks: List[WeekModel],
                 app_type: ApplicationType):
        app_type = ApplicationType(app_type)
        ApplicationModel.validate_type(program_id, app_type)
        self.no = ApplicationModel.get_next_no(program_id)
        self.program_id = program_id
        self.type = app_type
        self.contracts = contracts
        self.weeks = weeks
        self.save_to_db()

    def __str__(self):
        return f"{self.program.semester_no}/{self.no}/{self.program.school_year}"

    def get_str_name(self):
        return f"{self.program.semester_no}_{self.no}_{self.program.school_year.replace('/', '_')}_{ApplicationType.convert_to_str(self.type)}"

    def get_dir(self):
        main = config_parser.get("Directories", "application")
        return path.join(main, self.get_str_name())

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
            raise ValueError("Jeden program musi zawierać wszystkie wnioski całościowe lub częściowe: owoce-nabiał i nabiał")

    @staticmethod
    def get_next_no(program_id):
        return ApplicationModel.all_filtered_by_program(program_id).count() + 1

    def json(self):
        data: {} = super().json()
        data["type"] = ApplicationType.convert_to_str(self.type)
        data["contracts"] = [contract.json() for contract in self.contracts]
        data["weeks"] = [week.json() for week in self.weeks]
        return data
