import enum

from helpers.date_converter import DateConverter
from helpers.db import db
from models.application import ApplicationType, ApplicationModel
from models.base_database_query import BaseDatabaseQuery
from models.contract import ContractModel
from models.product import ProductTypeModel
from models.week import WeekModel
from helpers.logger import app_logger


class RecordState(enum.Enum):
    PLANNED = 1
    GENERATED = 2
    DELIVERED = 3
    GENERATION_IN_PROGRESS = 4
    DELIVERY_PLANNED = 5
    ASSIGN_NUMBER = 6


class RecordNumbersChangedError(Exception):
    def __str__(self):
        return f"Zmienione zostały numery WZ dla szkoły: {self.args[0] if len(self.args) else ''}"


class RecordModel(db.Model, BaseDatabaseQuery):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    no = db.Column(db.Integer, nullable=True)
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
        self.add_to_db()

    def is_in_middle(self):
        is_current_dairy_type = ProductTypeModel.find_by_id(self.product_type_id).is_dairy()
        previous_records_no = [record.no for record in
                               RecordModel.query.join(RecordModel.contract).filter_by(id=self.contract_id).order_by(
                                   RecordModel.no)
                               if ProductTypeModel.find_by_id(record.product_type_id).is_dairy() == is_current_dairy_type]
        return self.no != previous_records_no[-1]

    def __assign_record_no(self) -> bool:
        is_current_dairy_type = ProductTypeModel.find_by_id(self.product_type_id).is_dairy()
        previous_records_no = [record for record in RecordModel.query.join(RecordModel.contract).filter_by(id=self.contract_id).order_by(RecordModel.date)
                               if ProductTypeModel.find_by_id(record.product_type_id).is_dairy() == is_current_dairy_type]
        numbers_changed = False
        for i in range(len(previous_records_no)):
            if previous_records_no[i].no != i + 1:
                if previous_records_no[i].no:
                    previous_records_no[i].no = i + 1
                    numbers_changed = True
                    app_logger.debug(f"Overriding the number for {repr(self)} {previous_records_no[i].no} -> {i+1}")
                elif previous_records_no[i].date == self.date:
                    previous_records_no[i].no = i + 1
        return numbers_changed

    def get_record_no(self):
        product_prefix = "NB" if ProductTypeModel.find_by_id(self.product_type_id).is_dairy() else "WO"
        if self.no:
            return f"{product_prefix} {self.no}/{self.contract.contract_no}/{self.contract.program}"
        else:
            return f"-"

    def __str__(self):
        return f"{self.product_store.product.name}  {self.delivered_kids_no}"

    def __repr__(self):
        return f"Date: {self.date} {self.product_store.product.name} {self.contract.school.nick}"

    @classmethod
    def find(cls, date, product_type: ProductTypeModel, contract_id):
        return cls.query.filter_by(date=DateConverter.convert_to_date(date), product_type_id=product_type.id,
                                   contract_id=contract_id).first()

    @classmethod
    def all_filtered_by_program(cls, program_id):
        return cls.query.join(cls.product_store).filter_by(program_id=program_id)

    @classmethod
    def all_filtered_by_week(cls, week_id):
        return cls.query.filter_by(week_id=week_id).join(cls.product_store)

    def json(self):
        data: {} = super().json()
        DateConverter.replace_date_to_converted(data, "date")
        DateConverter.replace_date_to_converted(data, "delivery_date")
        if data["state"]:
            data["state"] = RecordState(data["state"]).name
        data["product_type"] = ProductTypeModel.find_by_id(data["product_type_id"]).json()
        data["no"] = self.get_record_no()
        del data["product_type_id"]
        return data

    def change_state(self, state, **kwargs):
        numbers_changed = False
        if isinstance(state, int):
            state = RecordState(state)
        if state == RecordState.GENERATION_IN_PROGRESS:
            self.delivery_date = DateConverter.convert_to_date(kwargs["date"])
            self.delivered_kids_no = self.contract.get_kids_no(product_type=self.product_store.product.type,
                                                               date=self.date)
        elif state == RecordState.ASSIGN_NUMBER:
            numbers_changed = self.__assign_record_no()
        elif state == RecordState.PLANNED:
            self.delivery_date = None
            self.delivered_kids_no = None
            if "product_store_id" in kwargs:
                _store_id = kwargs["product_store_id"]
                self.product_store_id = _store_id

        self.state = state
        self.update_db_only()
        if numbers_changed:
            raise RecordNumbersChangedError(self.contract.school.nick)

    @classmethod
    def get_records(cls, ids):
        return [cls.find_by_id(_id) for _id in ids]

    @classmethod
    def filter_records(cls, application: ApplicationModel, state=RecordState.DELIVERED):
        weeks = [week.id for week in application.weeks]
        contracts = [contract.id for contract in application.contracts]
        product_types = []
        if application.type == ApplicationType.DAIRY or application.type == ApplicationType.FULL:
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.DAIRY_TYPE).id)
        if application.type == ApplicationType.FRUIT_VEG or application.type == ApplicationType.FULL:
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.FRUIT_TYPE).id)
            product_types.append(ProductTypeModel.find_one_by_name(ProductTypeModel.VEGETABLE_TYPE).id)
        return cls.query.filter(cls.state == state,
                                cls.week_id.in_(weeks),
                                cls.contract_id.in_(contracts),
                                cls.product_type_id.in_(product_types)).order_by(RecordModel.date).all()

    @classmethod
    def filter_records_by_contract(cls, application: ApplicationModel, contract: ContractModel,
                                   state=RecordState.DELIVERED):
        records = cls.filter_records(application, state)
        return [record for record in records if record.contract_id == contract.id]
