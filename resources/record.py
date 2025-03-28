import enum
from typing import List
from flask import request
from flask_restful import Resource
from marshmallow import fields, Schema, ValidationError, validate
from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from helpers.schema_validators import program_schema, DateQuerySchema, ProgramQuerySchema
from models.contract import ContractModel
from models.product import ProductStoreModel, ProductTypeModel
from models.record import RecordModel, RecordState
from models.school import SchoolModel
from tasks.generate_delivery_task import queue_delivery, queue_week_summary
from helpers.logger import app_logger
from models.week import WeekModel
from helpers.db import db
from tasks.generate_register_task import queue_record_register


def must_not_be_empty(data):
    if not data:
        raise ValidationError("Pole nie może być puste")

class BulkDeleteSchema(ProgramQuerySchema):
    ids = fields.List(fields.Int(required=True), required=True)

class RecordStateSchema(Schema):
    state = fields.Int(required=True, validate=validate.Range(RecordState.PLANNED.value, RecordState.DELIVERED.value))
    product_store_id = fields.Int(required=False)


class SchoolNickSchema(Schema):
    nick = fields.Str(required=True)
    products = fields.List(fields.Str(required=True), required=True)


class RecordsAllSchema(DateQuerySchema):
    records = fields.List(fields.Nested(SchoolNickSchema), validate=must_not_be_empty)


class CreateRecordSchema(DateQuerySchema):
    driver = fields.String(required=False)


class CreateRecordBodySchema(Schema):
    records = fields.List(fields.Int(required=True))
    boxes = fields.List(fields.Int(required=False))
    comments = fields.String(required=False)


class RecordAdditionResult(enum.Enum):
    SUCCESS = 0
    RECORD_OF_THIS_TYPE_EXISTS = 1
    MIN_AMOUNT_EXCEED = 2
    NO_CONTRACT_FOR_PRODUCT_TYPE = 3
    FAILED_WITH_OTHER_REASON = 4


class RecordResponse:
    def __init__(self, nick, product, result: RecordAdditionResult = RecordAdditionResult.FAILED_WITH_OTHER_REASON,
                 record_id=None):
        self.record_id = record_id
        self.result = result
        self.product = product
        self.nick = nick

    def __str__(self):
        return f"{self.__class__.__name__}: {self.nick} {self.product}: " \
               f"{self.record_id if self.record_id else 'not generated'}"

    def __repr__(self):
        return self.__str__()

    def json(self):
        data = {'nick': self.nick, 'product': self.product, 'result': self.result.value}
        if self.result == RecordAdditionResult.SUCCESS:
            data['record'] = RecordModel.find_by_id(self.record_id).json()
        return data


def is_contract_valid(product_store: ProductStoreModel, contract: ContractModel):
    if product_store.product.type.is_dairy():
        return not contract.invalid_dairy_contract()
    if product_store.product.type.is_fruit_veg():
        return not contract.invalid_fruit_veg_contract()


def try_to_insert_record(program_id, date, record_response) -> RecordResponse:
    product_store: ProductStoreModel = ProductStoreModel.find_by(program_id, record_response.product)
    if product_store:
        contract = ContractModel.find(program_id, SchoolModel.find_one_by_nick(record_response.nick).id)
        check_other_type = product_store.product.type.get_complementary_type() if product_store.product.type.is_fruit_veg() else False
        if RecordModel.find(date, product_type=product_store.product.type, contract_id=contract.id):
            record_response.result = RecordAdditionResult.RECORD_OF_THIS_TYPE_EXISTS
        elif check_other_type and RecordModel.find(date, product_type=ProductTypeModel.find_by(name=check_other_type),
                                                   contract_id=contract.id):
            record_response.result = RecordAdditionResult.RECORD_OF_THIS_TYPE_EXISTS
        elif not is_contract_valid(product_store, contract):
            record_response.result = RecordAdditionResult.NO_CONTRACT_FOR_PRODUCT_TYPE
        elif product_store.is_min_amount_exceeded(record_response.nick):
            record_response.result = RecordAdditionResult.MIN_AMOUNT_EXCEED
        else:
            try:
                rc = RecordModel(date=date, contract_id=contract.id, product_store=product_store)
                rc.save_to_db()
                record_response.result = RecordAdditionResult.SUCCESS
                record_response.record_id = rc.id
            except ValueError as e:
                record_response.result = RecordAdditionResult.FAILED_WITH_OTHER_REASON
                app_logger.error(f"Failed to insert new Record due to {e}")
    return record_response


class RecordsAllResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def post(cls):
        errors = program_schema.validate(request.args)
        body_errors = RecordsAllSchema().validate(request.json)
        if errors or body_errors:
            return {"message": f"url: {errors} body: {body_errors}"}, 400
        results: List[RecordResponse] = []
        date = request.json["date"]
        program_id = request.args["program_id"]
        for record in request.json["records"]:
            school_nick = record["nick"]
            for product in record["products"]:
                record_response = RecordResponse(nick=school_nick, product=product)
                results.append(try_to_insert_record(date=date,
                                                    program_id=program_id,
                                                    record_response=record_response))
        return {
                   "date": date,
                   "records": [res.json() for res in results]
               }, 200

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls):
        errors = program_schema.validate(request.args)
        if errors:
            return {"message": f"url: {errors}"}, 400
        results = RecordModel.all_filtered_by_program(request.args["program_id"])
        return {
                   "records": [res.json() for res in results]
               }, 200


class RecordResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, record_id):
        record = RecordModel.find_by_id(record_id)
        if not record:
            return {"message": f"Nie istnieje WZtka o zadanym id: {record_id}"}, 404
        return {
                   "record": record.json()
               }, 200

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls, record_id):
        body_errors = RecordStateSchema().validate(request.json)
        if body_errors:
            return {"message": f"{body_errors}"}, 400
        record: RecordModel = RecordModel.find_by_id(record_id)
        if not record:
            return {"message": f"Nie istnieje WZtka o zadanym id: {record_id}"}, 404
        try:
            record.change_state(**request.json)
            db.session.commit()
        except ValueError as e:
            app_logger.warn(f"Failed to change state of record {record_id} due to {e}")
            return {"message": f"{e}"}, 400
        return {
            "record": record.json()
        }

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def delete(cls, record_id):
        record: RecordModel = RecordModel.find_by_id(record_id)
        if not record:
            return {"message": f"Record with id {record_id} not found"}, 404
        is_in_middle = record.is_in_middle()
        record.delete_from_db()

        return {
                   'deleted_record': record.id,
                   'is_in_middle': is_in_middle
               }, 200


def validate_record(record: RecordModel, program_id):
    if not record or record.contract.program_id != program_id:
        return False
    return True


class RecordBulkDelete(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def delete(cls):
        errors = BulkDeleteSchema().validate(request.json)
        if errors:
            return { "message": f"{errors}" }, 400
        return RecordModel.bulk_delete(**request.json), 200


class RecordDeliveryCreate(Resource):

    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls):
        errors = CreateRecordSchema().validate(request.args)
        body_errors = CreateRecordBodySchema().validate(request.json)
        if errors or body_errors:
            return {"message": f"url: {errors} body: {body_errors}"}, 400
        records_ids = request.json["records"]
        records = RecordModel.get_records(records_ids)
        if any(record.state == RecordState.GENERATION_IN_PROGRESS for record in records):
            return {
                       "message": f"Jedna z WZtek jest już dodana do generującej się dostawy, poczekaj na koniec generowania.",
                       "records": [record.json() for record in records]
                   }, 400
        return queue_delivery(request)


class SummarizeDeliveryCreate(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, week_id):
        records = RecordModel.all_filtered_by_week(week_id).all()
        week = WeekModel.find_by_id(week_id)
        if len(records) == 0:
            return {
                "message": f"Nie znaleziono WZtek dla tygodnia: {week}"
            }, 400
        return queue_week_summary(week_id)


class RecordRegister(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, program_id):
        try:
            return queue_record_register(program_id)
        except ValueError as e:
            return {'error': f"{e}"}, 400
