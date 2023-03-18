import sqlalchemy.exc
from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from helpers.date_converter import DateConverter


class WeekModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'week'

    id = db.Column(db.Integer, primary_key=True)
    week_no = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)

    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel', backref=db.backref('weeks', lazy=True))
    __table_args__ = (db.UniqueConstraint('week_no', 'program_id'),)

    def __init__(self, week_no, start_date, end_date, program_id):
        if start_date >= end_date:
            raise ValueError(f"Start date: {start_date} cannot be after end date: {end_date}")
        self.week_no = week_no
        self.start_date = start_date
        self.end_date = end_date
        self.program_id = program_id
        self.save_to_db()

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "start_date")
        DateConverter.replace_date_to_converted(data, "end_date")
        return data

    def __str__(self):
        return f"{self.week_no}: {self.start_date} - {self.end_date}"

    @classmethod
    def find_by_date(cls, date):
        try:
            res = cls.query.filter(WeekModel.start_date <= date).filter(date <= WeekModel.end_date).one()
        except sqlalchemy.exc.MultipleResultsFound:
            raise ValueError(f"More than one week found for date: {date}. Weeks should never overlap.")
        return res

    @classmethod
    def find(cls, week_no, program_id):
        return cls.query.filter_by(week_no=week_no, program_id=program_id).first()

    @staticmethod
    def prepare_str_from_weeks(weeks):
        return ",".join(["{0}-{1}".format(DateConverter.convert_date_to_string(week.start_date),
                                          DateConverter.convert_date_to_string(week.end_date)) for week in weeks])
