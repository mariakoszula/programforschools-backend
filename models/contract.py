import enum

from helpers.date_converter import DateConverter, is_date_in_range
from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from models.product import ProductTypeModel
from models.program import ProgramModel
from models.school import SchoolModel


def get_kids_no_by_type(contract_or_annex, product_type: ProductTypeModel):
    if product_type.is_dairy():
        return contract_or_annex.dairy_products
    if product_type.is_fruit_veg():
        return contract_or_annex.fruitVeg_products


class ContractModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'contract'
    id = db.Column(db.Integer, primary_key=True)
    contract_no = db.Column(db.String(80), nullable=False)
    contract_year = db.Column(db.Integer, nullable=False)
    validity_date = db.Column(db.DateTime, nullable=False)
    fruitVeg_products = db.Column(db.Integer, default=0)
    dairy_products = db.Column(db.Integer, default=0)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    school = db.relationship('SchoolModel',
                             backref=db.backref('contract', lazy=True, order_by='ContractModel.validity_date.desc()'))
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    program = db.relationship('ProgramModel',
                              backref=db.backref('contract', lazy=True, order_by='ContractModel.contract_no.desc()'))
    __table_args__ = (db.UniqueConstraint('program_id', 'school_id'),)

    def invalid_fruit_veg_contract(self):
        return self.fruitVeg_products == 0

    def invalid_dairy_contract(self):
        return self.dairy_products == 0

    def __init__(self, school_id, program: ProgramModel):
        self.school_id = school_id
        self.program_id = program.id
        self.contract_no = len(program.contract) + 1
        self.contract_year = DateConverter.get_year()
        self.validity_date = program.start_date

    def __str__(self):
        return f"{self.contract_no}_{self.contract_year}"

    def __repr__(self):
        return f"{str(self)} {self.validity_date}"

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "validity_date")
        data['school'] = SchoolModel.find_by_id(self.school_id).json()
        data['annex'] = [annex.json() for annex in self.annex]
        return data

    def get_kids_no(self, product_type: ProductTypeModel, date):
        if not len(self.annex):
            return get_kids_no_by_type(self, product_type)
        else:
            for annex in self.annex:
                end_date = self.program.end_date if not annex.timed_annex \
                    else annex.timed_annex[0].validity_date_end
                if is_date_in_range(date, annex.validity_date, end_date):
                    return get_kids_no_by_type(annex, product_type)
            if is_date_in_range(date, self.validity_date, self.program.end_date):
                return get_kids_no_by_type(self, product_type)
        raise ValueError(f"Failed to find kids no for {date}: {self}")

    @classmethod
    def find(cls, program_id, school_id):
        return cls.query.filter_by(program_id=program_id, school_id=school_id).first()


class AnnexModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'annex'
    id = db.Column(db.Integer, primary_key=True)

    no = db.Column(db.Integer, nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    contract = db.relationship('ContractModel',
                               backref=db.backref('annex', lazy=True, order_by='AnnexModel.validity_date.desc()'))
    validity_date = db.Column(db.DateTime, nullable=False)
    fruitVeg_products = db.Column(db.Integer, nullable=False)
    dairy_products = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('contract_id', 'no'),)

    def __init__(self, contract, validity_date, *, fruitVeg_products=None, dairy_products=None, validity_date_end=None):
        if validity_date_end and \
                DateConverter.convert_to_date(validity_date_end) < DateConverter.convert_to_date(validity_date):
            raise ValueError(f"Failed to create annex {validity_date_end} < {validity_date}")
        self.contract_id = contract.id
        self.validity_date = validity_date
        self.fruitVeg_products = fruitVeg_products if fruitVeg_products else contract.fruitVeg_products
        self.dairy_products = dairy_products if dairy_products else contract.dairy_products
        self.no = len(contract.annex) + 1
        self.save_to_db()
        if validity_date_end:
            TimedAnnexModel(validity_date_end, self.id).save_to_db()

    def __str__(self):
        return f"{self.no}: {self.contract.contract_no}_{self.contract.contract_year} - {self.validity_date}"

    def __repr__(self):
        return str(self)

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "validity_date")
        if len(self.timed_annex) == 1:
            data['validity_date_end'] = self.timed_annex[0].json()["validity_date_end"]
        else:
            data['validity_date_end'] = None
        return data

    @classmethod
    def find(cls, no, contract_id):
        return cls.query.filter_by(no=no, contract_id=contract_id).first()

    @classmethod
    def find_by_date(cls, validity_date, contract_id):
        return cls.query.filter_by(validity_date=validity_date, contract_id=contract_id).first()

    def get_validity_date_end(self, empty=""):
        if self.timed_annex:
            timed_annex = self.timed_annex[0]
            return DateConverter.convert_date_to_string(timed_annex.validity_date_end)
        return empty


class TimedAnnexModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'timed_annex'
    id = db.Column(db.Integer, primary_key=True)
    validity_date_end = db.Column(db.DateTime, nullable=False)
    annex_id = db.Column(db.Integer, db.ForeignKey('annex.id'), nullable=False)
    annex = db.relationship('AnnexModel', backref=db.backref('timed_annex', lazy=True))
    __table_args__ = (db.UniqueConstraint('annex_id'),)

    def __init__(self, validity_date_end, annex_id):
        self.validity_date_end = validity_date_end
        self.annex_id = annex_id
        self.save_to_db()

    @classmethod
    def find(cls, annex_id):
        return cls.query.filter_by(annex_id=annex_id).first()

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "validity_date_end")
        return data


class SuspendType(enum.Enum):
    LOCKDOWN = 0
    QUARANTINE = 1
