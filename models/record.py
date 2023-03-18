import enum
from typing import List

from helpers.date_converter import DateConverter
from helpers.db import db
from models.application import ApplicationType, ApplicationModel
from models.base_database_query import BaseDatabaseQuery
from models.contract import ContractModel
from models.product import ProductModel, ProductTypeModel, ProductStoreModel
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
        if isinstance(state, int):
            state = RecordState(state)
        if state == RecordState.GENERATION_IN_PROGRESS:
            self.delivery_date = DateConverter.convert_to_date(kwargs["date"])
            self.delivered_kids_no = self.contract.get_kids_no(product_type=self.product_store.product.type,
                                                               date=self.date)
        elif state == RecordState.PLANNED:
            self.delivery_date = None
            self.delivered_kids_no = None
            if "product_store_id" in kwargs:
                _store_id = kwargs["product_store_id"]
                product_store: ProductStoreModel = ProductStoreModel.find_by_id(_store_id)
                if product_store.product.type_id != self.product_type_id:
                    raise ValueError("Product type mismatch")
                self.product_store_id = _store_id

        self.state = state
        self.update_db()

    @classmethod
    def get_records(cls, ids):
        return [cls.find_by_id(_id) for _id in ids]

    @classmethod
    def filter_records(cls, application: ApplicationModel, state=RecordState.DELIVERED):
        weeks = [week.id for week in application.weeks]
        contracts = [contract.id for contract in application.contracts]
        product_types = []
        if application.type == ApplicationType.DAIRY:
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.DAIRY_TYPE).id)
        elif application.type == ApplicationType.FRUIT_VEG:
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.FRUIT_TYPE).id)
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.VEGETABLE_TYPE).id)
        return cls.query.filter(cls.state == state,
                                cls.week_id.in_(weeks),
                                cls.contract_id.in_(contracts),
                                cls.product_type_id.in_(product_types)).order_by(RecordModel.date).all()

    @classmethod
    def filter_records_by_contract(cls, application: ApplicationModel, contract: ContractModel):
        records = cls.filter_records(application)
        return [record for record in records if record.contract_id == contract.id]
