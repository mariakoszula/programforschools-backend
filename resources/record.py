import enum
from typing import List

from flask import request
from flask_restful import Resource
from marshmallow import fields, Schema, ValidationError, validate

from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from documents_generator.DeliveryGenerator import DeliveryGenerator
from documents_generator.RecordGenerator import RecordGenerator
from helpers.common import generate_documents
from models.base_database_query import program_schema, DateQuerySchema
from models.contracts import ContractModel
from models.product import ProductStoreModel, ProductBoxModel
from models.record import RecordModel, RecordState
from models.school import SchoolModel


def must_not_be_empty(data):
    if not data:
        raise ValidationError("Must not be empty")


class RecordStateSchema(Schema):
    state = fields.Int(required=True, validate=validate.Range(RecordState.PLANNED.value, RecordState.DELIVERED.value))


class SchoolNickSchema(Schema):
    nick = fields.Str(required=True)
    products = fields.List(fields.Str(required=True), required=True)


class RecordsAllSchema(DateQuerySchema):
    records = fields.List(fields.Nested(SchoolNickSchema), validate=must_not_be_empty)


class CreateRecordSchema(DateQuerySchema):
    driver = fields.String(required=True)


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
        if RecordModel.find(date, product=product_store.product, contract_id=contract.id):
            record_response.result = RecordAdditionResult.RECORD_OF_THIS_TYPE_EXISTS
        elif not is_contract_valid(product_store, contract):
            record_response.result = RecordAdditionResult.NO_CONTRACT_FOR_PRODUCT_TYPE
        elif product_store.is_min_amount_exceeded(record_response.nick):
            record_response.result = RecordAdditionResult.MIN_AMOUNT_EXCEED
        else:
            rc = RecordModel(date=date, contract_id=contract.id, product_store=product_store)
            rc.save_to_db()
            record_response.result = RecordAdditionResult.SUCCESS
            record_response.record_id = rc.id
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
            return {"message": f"Record with id {record_id} not found"}, 404
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
            return {"message": f"Record with id {record_id} not found"}, 404
        record.update_db(state=RecordState(request.json['state']))
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
        record.delete_from_db()
        return {
                   'deleted_record': record.id
               }, 200


def validate_record(record: RecordModel, program_id):
    if not record or record.contract.program_id != program_id:
        return False
    return True


class RecordDeliveryResource(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def put(cls):
        errors = CreateRecordSchema().validate(request.args)
        body_errors = CreateRecordBodySchema().validate(request.json)
        if errors or body_errors:
            return {"message": f"url: {errors} body: {body_errors}"}, 400
        records = [RecordModel.find_by_id(_id) for _id in request.json["records"]]
        boxes = [ProductBoxModel.find_by_id(_id) for _id in request.json["boxes"]]
        delivery_date = request.args["date"]
        for record in records:
            record.change_state(RecordState.GENERATED, date=delivery_date)
        uploaded_documents = []
        for record in records:
            uploaded_documents.extend(generate_documents(gen=RecordGenerator, record=record))
        uploaded_documents.extend(generate_documents(gen=DeliveryGenerator,
                                                     records=records,
                                                     **request.args,
                                                     boxes=boxes,
                                                     comments=request.json["comments"]))
        return {
                   'documents': uploaded_documents
               }, 200
