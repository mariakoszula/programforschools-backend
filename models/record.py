import enum

from helpers.date_converter import DateConverter
from helpers.db import db
from models.base_database_query import BaseDatabaseQuery
from models.product import ProductModel, ProductTypeModel
from models.week import WeekModel


class RecordState(enum.Enum):
    PLANNED = 1
    GENERATED = 2
    DELIVERED = 3
    GENERATION_IN_PROGRESS = 4


class RecordModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    delivery_date = db.Column(db.DateTime, nullable=True)
    delivered_kids_no = db.Column(db.Integer, nullable=True)
    state = db.Column(db.Enum(RecordState), nullable=False)
    product_store_id = db.Column(db.Integer, db.ForeignKey('product_store.id'), nullable=False)
    product_store = db.relationship('ProductStoreModel',
                                    backref=db.backref('records', lazy=True))
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    contract = db.relationship('ContractModel',
                               backref=db.backref('records', lazy=True, cascade="all, delete-orphan"))
    week_id = db.Column(db.Integer, db.ForeignKey('week.id'), nullable=False)
    week = db.relationship('WeekModel',
                           backref=db.backref('records', lazy=True))

    __table_args__ = (db.UniqueConstraint('date', 'product_type_id', 'contract_id'),)

    def __init__(self, date, contract_id, product_store):
        self.date = DateConverter.convert_to_date(date)
        self.state = RecordState.PLANNED
        self.product_store_id = product_store.id
        self.contract_id = contract_id
        self.week_id = WeekModel.find_by_date(self.date).id
        self.product_type_id = product_store.product.type.id

    def __str__(self):
        return f"{self.product_store.product.name}  {self.delivered_kids_no}"

    def __repr__(self):
        return f"Date: {self.date} {self.product_store.product.name} {self.contract.school.nick}"

    @classmethod
    def find(cls, date, product: ProductModel, contract_id):
        return cls.query.filter_by(date=DateConverter.convert_to_date(date), product_type_id=product.type.id,
                                   contract_id=contract_id).first()

    @classmethod
    def all_filtered_by_program(cls, program_id):
        return cls.query.join(cls.product_store).filter_by(program_id=program_id)

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "date")
        DateConverter.replace_date_to_converted(data, "delivery_date")
        if data["state"]:
            data["state"] = RecordState(data["state"]).name
        data["product_type"] = ProductTypeModel.find_by_id(data["product_type_id"]).json()
        del data["product_type_id"]
        return data

    def change_state(self, state, **kwargs):
        if state == RecordState.GENERATION_IN_PROGRESS:
            self.delivery_date = DateConverter.convert_to_date(kwargs["date"])
        if state == RecordState.GENERATED:
            self.delivered_kids_no = self.contract.get_kids_no(product_type=self.product_store.product.type,
                                                               date=self.date)

        self.state = state
        self.update_db()

    @classmethod
    def get_records(cls, ids):
        return [cls.find_by_id(_id) for _id in ids]
