from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from helpers.date_converter import DateConverter
from helpers.config_parser import config_parser


class ProgramModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'program'

    id = db.Column(db.Integer, primary_key=True)
    semester_no = db.Column(db.Integer, nullable=False)
    school_year = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    fruitVeg_price = db.Column(db.Float)
    dairy_price = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    dairy_min_per_week = db.Column(db.Integer)
    fruitVeg_min_per_week = db.Column(db.Integer)
    dairy_amount = db.Column(db.Integer)
    fruitVeg_amount = db.Column(db.Integer)

    company = db.relationship('CompanyModel')

    __table_args__ = (db.UniqueConstraint('school_year', 'semester_no'),)

    def __init__(self, semester_no, school_year, company_id, fruitVeg_price=None, dairy_price=None,
                 start_date=None, end_date=None, dairy_min_per_week=None, fruitVeg_min_per_week=None,
                 dairy_amount=None, fruitVeg_amount=None):
        self.fruitVeg_amount = fruitVeg_amount
        self.dairy_amount = dairy_amount
        self.fruitVeg_min_per_week = fruitVeg_min_per_week
        self.dairy_min_per_week = dairy_min_per_week
        self.end_date = end_date
        self.start_date = start_date
        self.semester_no = semester_no
        self.school_year = school_year
        self.company_id = company_id
        self.fruitVeg_price = fruitVeg_price
        self.dairy_price = dairy_price

    def __repr__(self):
        return f"Program: {self.id} semester_no:{self.semester_no} year:{self.school_year}"

    @classmethod
    def find(cls, school_year, semester_no):
        return cls.query.filter_by(semester_no=semester_no, school_year=school_year).first()

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "start_date")
        DateConverter.replace_date_to_converted(data, "end_date")
        return data

    def get_current_semester(self):
        if self.semester_no == 1:
            return "I"
        elif self.semester_no == 2:
            return "II"
        raise ValueError(f"Not supported semester number {self.semester_no}")

    def get_main_dir(self):
        return f"{config_parser.get('Directories', 'main_dir_program_part')}_" \
               f"{self.get_part_with_year_and_sem()}"

    def get_part_with_year_and_sem(self):
        school_year = self.school_year
        if "/" in self.school_year:
            school_year = self.school_year.replace("/", "_")
        return f"{school_year}_" \
               f"{config_parser.get('Directories', 'main_sem_dir_part')}_{self.semester_no}"
